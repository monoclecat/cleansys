{% comment %}
If using PyCharm, go to Preferences > Languages & Frameworks > Template Languages, 
and add Markdown to the Template file types. 
{% endcomment %}
Hallo {{ cleaner }}! 

{% block content %}
    
{% endblock %}

Mit freundlichen Grüßen,  
Dein Putzplan-System

P.S.: Du kannst deine Email-Benachrichtigungen <a href="{{ host }}{% url 'webinterface:cleaner-edit' cleaner.pk %}">hier</a> anpassen.
