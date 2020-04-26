{% extends 'email_templates/email_base_template.md' %}

{% block content %}
Du bekommst diese Email, da du entweder neu zum Putzplan-System dazu gekommen bist oder weil deine Email-Addresse geändert wurde. 

## Willkommen im Putzplan-System CleanSys!

Ich freue mich, dich als neues Mitglied begrüßen zu dürfen. 

Falls CleanSys dir neu ist, empfehle ich dir <a href="{{ host }}{% url 'webinterface:docs' %}">die Einführung</a> zu lesen.  
{% endblock %}
