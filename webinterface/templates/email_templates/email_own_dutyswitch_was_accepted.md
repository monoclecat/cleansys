{% extends 'email_templates/email_base_template.md' %}

{% block content %}
Am {{ dutyswitch.created|date:"d. b. Y" }} hast du eine Tauschanfrage für deinen Putzdienst am **{{ dutyswitch.requester_assignment.assignment_date|date:"d. b. Y" }}** 
im Putzplan **{{ dutyswitch.requester_assignment.schedule }}** erstellt. 

**{{ acceptor_cleaner }}** hat diese Tauschanfrage nun angenommen und übernimmt damit deinen Putzdienst am {{ dutyswitch.requester_assignment.assignment_date|date:"d. b. Y" }}. 

Dein neuer Putzdienst im Putzplan {{ dutyswitch.requester_assignment.schedule }} ist nun am **{{ dutyswitch.acceptor_assignment.assignment_date|date:"d. b. Y" }}**. 
{% endblock %}
