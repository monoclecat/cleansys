{% extends 'email_templates/email_base_template.md' %}

{% block content %}
{{ requester.cleaner }} möchte seinen/ihren Putzdienst am 
**{{ requester.assignment_date|date:"d. b. Y" }}** 
im Putzplan **{{ requester.schedule }}** tauschen, und du bist in der Lage, den Tausch anzunehmen! 

{{ requester.cleaner }}'s Begründung für die Tauschanfrage lautet: 

> "{{ dutyswitch.message }}"

Die folgenden Putzdienste im Putzplan **{{ requester.schedule }}** kannst du für 
{{ requester.cleaner }}'s Dienst tauschen:
{% for assignment in tradeable %}
- {{ assignment }}
{% empty %} 
*Es gibt keine tauschbaren Dienste*
{% endfor %}

Wenn du einen deiner Putzdienste tauschen möchtest, so beantworte bitte {{ requester.cleaner }}'s Tauschanfrage 
 <a href="{{ host }}{% url 'webinterface:dutyswitch-accept-no-cleaner-page' dutyswitch.pk %}">über diesen Link</a>. 
{% endblock %}
