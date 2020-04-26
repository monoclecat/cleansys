{% extends 'email_templates/email_base_template.md' %}

{% block content %}
Danke, dass du {{ requester_cleaner }}'s Putzdienst-Tauschanfrage im Putzplan {{ dutyswitch.requester_assignment.schedule }} angenommen hast!

{{ requester_cleaner }} übernimmt damit deinen Putzdienst am {{ dutyswitch.acceptor_assignment.assignment_date|date:"d. b. Y" }}. 

Dein neuer Putzdienst im Putzplan {{ dutyswitch.requester_assignment.schedule }} ist nun am **{{ dutyswitch.requester_assignment.assignment_date|date:"d. b. Y" }}**.
{% endblock %}
