{% extends 'email_templates/email_base_template.md' %}

{% block content %}
{{ requester.cleaner }} möchte seinen/ihren Putzdienst am 
**{{ requester.assignment_date|date:"d. b. Y" }}** 
im Putzplan **{{ requester.schedule }}** tauschen. 

Dein Dienst am {{ dutyswitch.proposed_acceptor.assignment_date|date:"d. b. Y" }} wurde zum 
Tausch vorgeschlagen. 
**Wenn du nicht auf diese Email reagierst, wird der Tausch nach dem 
{{ dutyswitch.execute_proposal|date:"d. b. Y" }} ausgeführt.**

Wenn dieser Vorschlag ok für dich ist, kannst du diese Email ignorieren. 
Wenn du stattdessen einen anderen PutzdienstV tauschen möchtest, kannst du das 
<a href="{{ host }}{% url 'webinterface:dutyswitch-accept-no-cleaner-page' dutyswitch.pk %}">hier tun</a>. 

Den Vorschlag einfach nur ablehnen kannst du 
<a href="{{ host }}{% url 'webinterface:dutyswitch-reject-proposal' dutyswitch.pk %}">hier</a>. 
Dann wird ein neuer Vorschlag unter allen möglichen Tauschzielen zufällig ausgewählt.  

{% endblock %}
