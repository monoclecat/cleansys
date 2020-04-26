{% extends 'email_templates/email_base_template.md' %}

{% block content %}
Am **{{ assignment.assignment_date|date:"l, d. b. Y" }}** hast du einen Putzdienst im Putzplan **{{ assignment.schedule }}**! 

{% with other_cleaners=assignment.other_cleaners_in_week_for_schedule.all %}
{% if other_cleaners %}
Diesen Putzdienst hast du zusammen mit {% for cleaner in other_cleaners %}**{{ cleaner.name }}**{% if not forloop.last %}, {% endif %}.
{% endfor %}
{% endif %}
{% endwith %}

Folgende Aufgaben sind mit diesem Putzdienst verbunden:

| **Aufgabe** | **Bearbeitbar von** | **Bearbeitbar bis** |  
| --- | --- | --- |  
{% for task in assignment.cleaning_week.task_set.all %}| **{{ task }}**&nbsp;&nbsp; | &nbsp;&nbsp;{{ task.start_date|date:"l, d. b. Y" }}&nbsp;&nbsp; | &nbsp;&nbsp;{{ task.end_date|date:"l, d. b. Y" }} |  
{% endfor %}

Nähere Informationen erhältst du wie gewohnt als Überblick auf deiner <a href="{{ host }}{% url 'webinterface:cleaner-no-page' %}">persönlichen Startseite</a>
oder direkt auf der <a href="{{ host }}{% url 'webinterface:assignment-tasks' assignment.cleaning_week.pk %}">Seite des hier genannten Putzdienstes</a>.
{% endblock %}
