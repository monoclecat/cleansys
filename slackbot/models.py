from django.db import models
from webinterface.models import Cleaner, CleaningDuty


class DutySwitch(models.Model):
    source_cleaner = models.ForeignKey('webinterface.Cleaner', on_delete=models.CASCADE)
    source_duty = models.ForeignKey('webinterface.CleaningDuty', on_delete=models.CASCADE)
    destinations = models.CharField(max_length=100)
    # destinations is a string representation of a list of lists [<cleanerpk>, <dutypk>] which are suitable candidates
    # for the source to switch with. Example: <cleanerpk>,<dutypk>;<cleanerpk>,<dutypk>;<cleanerpk>,<dutypk>
    # destinations is a FIFO type stack, the wish destination is always the first pair of PKs
    STATES = ((1, 'Waiting on destination approval'), (2, 'Waiting on source approval'))
    status = models.IntegerField(choices=STATES)
    # DutySwitch object gets created, as soon as Cleaner sends request with a wish Duty destination
    # status is set to 2 because we need approval from the destination to commence switching.
    # If the destination denies approval, status is set to 1 because the source needs to select a new
    # destination. The cycle begins from the start

    def parse_from_destinations(self):
        """Parses destinations field into a list and
        returns [wish destination pair], [[list of following destinations]]"""
        dest_list = []
        for pair in self.destinations.split(";"):
            dest_list.append([int(pk) for pk in pair.split(",")])
        if dest_list:
            return dest_list[0], dest_list[1:]
        else:
            return [], []

    def parse_to_destinations(self, dest_list):
        dest_string = ""
        for pair in dest_list:
            for pk in pair:
                dest_string += str(pk) + ","
            dest_string = dest_string[:-1]
            dest_string += ";"
        dest_string = dest_string[:-1]
        return dest_string

    def wish_destination_accepted(self):
        destination_pair, rest_of_list = self.parse_from_destinations()

        destination_cleaner = Cleaner.objects.get(pk=destination_pair[0])
        destination_duty = CleaningDuty.objects.get(pk=destination_pair[1])

        source_cleaner = Cleaner.objects.get(pk=self.source_cleaner)
        source_duty = CleaningDuty.objects.get(pk=self.source_duty)

        source_duty.excluded.add(source_cleaner)
        source_duty.cleaners.remove(source_cleaner)
        source_duty.cleaners.add(destination_cleaner)

        destination_duty.cleaners.remove(destination_cleaner)
        destination_duty.cleaners.add(source_cleaner)

        confirmation_text = "Dein Tausch war erfolgreich!"
        # TODO send confirmation to source and destination

    def wish_destination_rejected(self):
        destination_pair, rest_of_list = self.parse_from_destinations()

        self.destinations = self.parse_to_destinations(rest_of_list)

        confirmation_text = "Die Anfrage wurde erfolgreich abgelehnt"
        new_options_text = "Deine Anfrage wurde abgeleht. Wähle bitte eine der weiteren Optionen"

        # TODO send message to source with new options and confirmation to destination


