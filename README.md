# Item Catalog
A RESTful web application that provides a catalog of items as well as a user registration and authentication system. Registered users will have the ability to post, edit and delete their own items. The app also has JSON endpoints that serve the item information.

This application interacts with a sqlite database using SQLAlchemy, an Object-Relational Mapping (ORM) layer. The CRUD (create, read, update and delete) operations and web page templates are handled using Python Flask framework. OAuth 2.0 framework allows users to securely login to the application using Google+ Sign-In or Facebook Login so users can create items that are viewable by everyone but only modifiable by the original creator.

Version of Python used: 3.6.1

### Contents
Project files : <br/>
DatabaseSetup.py - Python program file that creates the sqllite database and related tables.<br/>
TestDataUpload.py - Data that can be loaded in the item catalog database tables.<br/>
projectFinal.py - File that runs the web application.<br/>
static and template folders with images, stylesheet and HTML templates.



### Installation
Install [Python](https://www.python.org )<br/>

**Install VirtualBox** <br/>
This project makes use of Linux-based virtual machine (VM). Vagrant and VirtualBox are used to install and manage the VM. VirtualBox is the software that runs the virtual machine. You can download it from [virtualbox.org](https://www.virtualbox.org/wiki/Downloads). Install the platform package for your operating system.

**Install Vagrant**<br/>
Vagrant is the software that configures the VM and lets share files between your host computer and the VM's filesystem. Download it from [vagrantup.com](https://www.vagrantup.com/downloads.html). Install the version for your operating system.<br/>
From your terminal, inside the vagrant subdirectory, run the command `vagrant up`. This will cause Vagrant to download the Linux operating system and install it. This may take quite a while. Then log into it with `vagrant ssh`.

Download the files into the vagrant directory, which is shared with your virtual machine.
<br/>


### Operating Instructions
To Start the item catalog application:<br/>
1. Open the command line tool<br/>
2. Inside the vagrant subdirectory(cd /vagrant), navigate to the directory containing downloaded files. </br>
3. Run `python3 DatabaseSetup.py` to create the sqlite database and corresponding tables<br/>
4. To load the data into tables, run the TestDataUpload.py file.</br>
5. Run `python3 projectFinal.py` to run the application.</br>
6. Open your web browser and connect to [localhost:5000](http://localhost:5000/catalog/). Item Catalog app page is loaded with catalog and items data if available and with an option to login <br/>
7. Authenticate using Google or Facebook Sign in to manage categories and their items.
