from webinterface.models import *
from markdown import markdown
from django.core import mail
from django.template.loader import get_template
from cleansys.settings import EMAIL_FROM_ADDRESS, BASE_URL_WITH_HOST


def create_email_message(subject, rendered_markdown, to):
    admin = User.objects.filter(is_superuser=True).first()
    html = markdown(rendered_markdown, extensions=['tables'])
    msg = mail.EmailMultiAlternatives(
        subject=subject,
        body=rendered_markdown,
        from_email=EMAIL_FROM_ADDRESS,
        to=[to],
        bcc=[EMAIL_FROM_ADDRESS],
        reply_to=[admin.email])
    msg.attach_alternative(html, "text/html")
    return msg


def send_welcome_email(cleaner):
    outbox = []

    template = get_template('email_templates/email_welcome.md')
    context = {  # for base_template, context MUST contain cleaner and host
        'cleaner': cleaner,
        'host': BASE_URL_WITH_HOST,
    }
    outbox.append(create_email_message(
        subject="Willkommen im Putzplan-System CleanSys!",
        rendered_markdown=template.render(context),
        to=cleaner.user.email))
    connection = mail.get_connection()
    connection.send_messages(outbox)


def send_email_changed(cleaner, previous_address):
    outbox = []

    template = get_template('email_templates/email_changed.md')
    context = {  # for base_template, context MUST contain cleaner and host
        'cleaner': cleaner,
        'host': BASE_URL_WITH_HOST,
        'previous_address': previous_address,
    }
    outbox.append(create_email_message(
        subject="Deine Email-Addresse wurde geändert",
        rendered_markdown=template.render(context),
        to=previous_address))
    connection = mail.get_connection()
    connection.send_messages(outbox)


def send_email__new_acceptable_dutyswitch(dutyswitch):
    cleaners = set(x.cleaner for x in dutyswitch.possible_acceptors()
                   if x.cleaner.email_pref_new_acceptable_dutyswitch and x.cleaner.user.email)
    outbox = []
    for cleaner in cleaners:
        tradeable_assignments = dutyswitch.possible_acceptors().filter(cleaner=cleaner).all()

        template = get_template('email_templates/email_new_acceptable_dutyswitch.md')
        context = {  # for base_template, context MUST contain cleaner and host
            'cleaner': cleaner,
            'host': BASE_URL_WITH_HOST,
            'dutyswitch': dutyswitch,
            'requester': dutyswitch.requester_assignment,
            'tradeable': tradeable_assignments,
        }
        outbox.append(create_email_message(
            subject="{} möchte einen Putzdienst tauschen".format(dutyswitch.requester_assignment.cleaner.name),
            rendered_markdown=template.render(context),
            to=cleaner.user.email))
    connection = mail.get_connection()
    connection.send_messages(outbox)


def send_email__dutyswitch_complete(dutyswitch):
    outbox = []

    # The Cleaners for requester and acceptor Assignments have already been switched in the DutySwitch.save() method.
    requester_cleaner = dutyswitch.acceptor_assignment.cleaner
    acceptor_cleaner = dutyswitch.requester_assignment.cleaner

    if requester_cleaner.email_pref_own_dutyswitch_accepted and requester_cleaner.user.email:
        template = get_template('email_templates/email_own_dutyswitch_was_accepted.md')
        context = {  # for base_template, context MUST contain cleaner and host
            'cleaner': requester_cleaner,
            'host': BASE_URL_WITH_HOST,
            'dutyswitch': dutyswitch,
            'acceptor_cleaner': acceptor_cleaner,
        }
        outbox.append(create_email_message(
            subject="{} hat deine Putzdienst-Tauschanfrage angenommen".format(acceptor_cleaner.name),
            rendered_markdown=template.render(context),
            to=requester_cleaner.user.email))

    if acceptor_cleaner.email_pref_accepted_foreign_dutyswitch and acceptor_cleaner.user.email:
        template = get_template('email_templates/email_accepted_foreign_dutyswitch.md')
        context = {  # for base_template, context MUST contain cleaner and host
            'cleaner': acceptor_cleaner,
            'host': BASE_URL_WITH_HOST,
            'dutyswitch': dutyswitch,
            'requester_cleaner': requester_cleaner,
        }
        outbox.append(create_email_message(
            subject="Du hast eine Putzdienst-Tauschanfrage angenommen",
            rendered_markdown=template.render(context),
            to=acceptor_cleaner.user.email))

    connection = mail.get_connection()
    connection.send_messages(outbox)


def send_email__assignment_coming_up(notify_days_before=5):
    from webinterface.models import Cleaner, current_epoch_week
    outbox = []
    for cleaner in Cleaner.objects.has_email().filter(email_pref_assignment_coming_up=True):
        assignments = cleaner.assignment_set.in_enabled_cleaning_weeks().\
            filter(cleaning_week__week__range=(current_epoch_week(), current_epoch_week()+1))

        notify = [x for x in assignments.all()
                  if x.assignment_date()-timezone.timedelta(days=notify_days_before) == timezone.now().date()]

        for assignment in notify:
            template = get_template('email_templates/email_assignment_coming_up.md')
            context = {  # for base_template, context MUST contain cleaner and host
                'cleaner': cleaner,
                'host': BASE_URL_WITH_HOST,
                'assignment': assignment,
            }
            outbox.append(create_email_message(
                subject="Dein Putzdienst in {} am {}".format(
                    assignment.schedule, assignment.assignment_date().strftime("%a, %d.%b.%Y")),
                rendered_markdown=template.render(context),
                to=cleaner.user.email))
    connection = mail.get_connection()
    connection.send_messages(outbox)


def send_email__warn_admin_assignments_running_out():
    from webinterface.models import Schedule
    schedules_with_warning = [x for x in Schedule.objects.enabled() if x.assignments_are_running_out()]
    if schedules_with_warning:
        outbox = []
        admin = User.objects.filter(is_superuser=True).first()
        template = get_template('email_templates/email_warn_admin_assignments_running_out.md')
        outbox.append(create_email_message(subject="CleanSys erfordert dein Eingreifen!",
                                           rendered_markdown=template.render(),
                                           to=admin.email))
        connection = mail.get_connection()
        connection.send_messages(outbox)


def send_email__warn_admin_cleaner_soon_homeless():
    from webinterface.models import Cleaner
    cleaners_with_warning = [x for x in Cleaner.objects.all() if x.is_homeless_soon(less_than_equal=False)]
    # less_than_equal=False prevents the email being sent every week for the same Cleaner
    if cleaners_with_warning:
        outbox = []
        admin = User.objects.filter(is_superuser=True).first()
        template = get_template('email_templates/email_warn_admin_cleaners_moving_out.md')
        outbox.append(create_email_message(subject="CleanSys erfordert vielleicht dein Eingreifen!",
                                           rendered_markdown=template.render(),
                                           to=admin.email))
        connection = mail.get_connection()
        connection.send_messages(outbox)


def send_email__warn_admin_tasks_forgotten():
    from webinterface.models import CleaningWeek, current_epoch_week
    this_week = current_epoch_week()
    relevant_cleaning_weeks = CleaningWeek.objects.filter(week__range=(this_week-1, this_week))
    for cleaning_week in relevant_cleaning_weeks.all():
        if all([task.has_passed() for task in cleaning_week.task_set.all()]) \
                and any([task.end_date() + timezone.timedelta(days=1) == timezone.now().date()
                         for task in cleaning_week.task_set.all()]):
            ratio = cleaning_week.ratio_of_completed_tasks()
            if ratio == 0.0:
                # No Task was completed
                all_forgotten = True
            elif ratio < 1.0:
                # Not all Tasks were completed
                all_forgotten = False
            else:
                continue
            outbox = []
            admin = User.objects.filter(is_superuser=True).first()
            template = get_template('email_templates/email_warn_admin_tasks_forgotten.md')
            context = {  # for base_template, context MUST contain cleaner and host
                'all_forgotten': all_forgotten,
                'host': BASE_URL_WITH_HOST,
                'cleaning_week': cleaning_week,
            }
            outbox.append(create_email_message(subject="Bei einem Putzdienst wurden Aufgaben vergessen",
                                               rendered_markdown=template.render(context),
                                               to=admin.email))
            connection = mail.get_connection()
            connection.send_messages(outbox)


