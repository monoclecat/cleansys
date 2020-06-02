## Achtung CleanSys Administrator

Im Putzplan **{{ cleaning_week.schedule }}** wurden in der Putzwoche vom *{{ cleaning_week.week_start|date:"d. b. Y" }}* bis *{{ cleaning_week.week_end|date:"d. b. Y" }}* {% if all_forgotten %}**ALLE AUFGABEN VERGESSEN**{% else %}einige Aufgaben vergessen{% endif %}. 

Folgende Putzende waren für diesen Putzdienst verantwortlich: {% for cleaner in cleaning_week.assigned_cleaners.all %}**{{ cleaner.name }}**{% if not forloop.last %}, {% endif %}{% endfor %}

Konkret handelt es sich um diese nicht-gemachten Aufgaben: 

| **Aufgabe** | **Bearbeitbar von** | **Bearbeitbar bis** |  
| --- | --- | --- |  
{% for task in cleaning_week.open_tasks.all %}| **{{ task }}**&nbsp;&nbsp; | &nbsp;&nbsp;{{ task.start_date|date:"l, d. b. Y" }}&nbsp;&nbsp; | &nbsp;&nbsp;{{ task.end_date|date:"l, d. b. Y" }} |  
{% endfor %}


Mit freundlichen Grüßen,  
dein Putzplan-System
