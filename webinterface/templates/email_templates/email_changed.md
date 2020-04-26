{% extends 'email_templates/email_base_template.md' %}

{% block content %}
Deine Email-Adresse wurde geändert! 

Alte Email: {{ previous_address }}  
Neue Email: {{ cleaner.user.email }}

Bei Fragen wende dich bitte an deinen Administrator. 
{% endblock %}
