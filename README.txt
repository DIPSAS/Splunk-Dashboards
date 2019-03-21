This folder contains the sourcecode for some useful Splunk dashboards for analyzing Splunk events.

-----------------------------------------------------------------------------------------------------------------------------
Add dashboard to Splunk
-----------------------------------------------------------------------------------------------------------------------------
To add a dashboard to Splunk, login to Splunk, select your app and go to the Dashboards view.
From here, select "Create New Dashboard"
NB: the title and description you add here will be overwritten when copying in the source code from the files in this folder!
The recommended ID of the new dashboard is the same as the filename for each board in this folder. 
The reason for having the same ID is so that possible links to other boards will work. 
If the ID is changed, so must the links to this board from other boards.

One example of this is the "projsta2019_error_context_and_analysis" board. 
Both the "projsta2019_client_error_overview" and "projsta2019_server_error_overview" boards link to this board 
via the details column in some of the tables on these boards.
So, if the ID of the error context and analysis board differs from "projsta2019_error_context_and_analysis", 
this needs to be reflected in both error overview boards for the links to work.

When the new board is created, select "Source" from the "Edit Dashboard" menu. 
Copy paste inn the source form the given file in this folder and save.

To make the board available for everyone, you need to set permissions from the "..." menu -> "Edit Permissions"