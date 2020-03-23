# Cleaning schedule management system (CleanSys)

CleanSys is a *cleaning schedule management system* written in Python (using the Django framework) which is built for 
non-stationary relationships between Cleaners and Schedules. 

In particular, CleanSys was built for a 15-person household with 4 floors. Each floor has its own weekly repeating 
cleaning schedules (such as for the bathroom), and the house itself has several biweekly-occurring schedules. 
While the cleaning schedules on each floor must only be cleaned by those living on that floor, the household-wide 
cleaning schedules must be cleaned by all inhabitants. 

The tricky part is (a) to make sure every Cleaner cleans his/her fair share in each cleaning schedule he is assigned
 to *(not cleaning too much or too little)*
and (b) to make sure a Cleaner isn't assigned 10 cleaning duties on one week-end, which would sure kill his/her free 
time and lead to frustration. 

Such a complex cleaning schedule system can either be planned on paper 
_(paper cleaning schedules were the way we did it prior to CleanSys, and 
took 2 hours every 3 months, the time taken corresponding directly to how well (a) and (b) were satisfied)_ 
or can be done electronically, which is a solution CleanSys provides. 

In addition, CleanSys offers a quick and easy way for Cleaners to switch duties with each other, if vacation is 
getting in the way of any cleaning duties 
_(the analogue version of this is to ask the group chat and hope for a response)_.

All this comes with powerful editing capabilities for the administrator, a simple interface for the Cleaners, 
simple click-on-your-name login if the Cleaners trust each other, and a strong focus on transparency (everyone can 
check if a Cleaner has done his duties). 

For work-intense cleaning schedules that split their (bi)weekly work-load on more than one cleaner, CleanSys 
shows who did which tasks. 

CleanSys is built for german cleaners, so the interface language is german. If you would like to have a translation 
(and are willing to put some effort into it yourself), please open an Issue for it. 


## Installation

## Playing around an exploring features
To start the CSG, run 'python manage.py runserver' and open 127.0.0.1:8000 in your browser. 
The admin area can be accessed with the credentials of the Django superuser: 

*Username:*admin  
*Password:*CleaningAdmin  

> WARNING: Make sure to change the superuser password when deploying the CSG! 

### First steps
