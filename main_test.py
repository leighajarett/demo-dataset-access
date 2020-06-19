from unittest.mock import Mock
import main

#test set for new trial
data = {
    "email": "leigha@looker.com",
    "name": "0064400000ssT5",
    "weeks": '3',
    "type" : 'Customer / Prospect'
    }

#test set for existing trial
data = {
    "email": "leigha@looker.com",
    "name": "0064400000ssT5",
    "weeks": 5,
    "type" : 'Customer / Prospect'
}

#test set for internal without a name
data = {
    "email": "leigha@looker.com",
    "type" : "Personal Development Instance"
    }

#test set for internal with a name
data = {
    "email": "leigha@looker.com",
    "name": "demoexpo",
    "type": "Internal Shared Instance"
    }

#test set for partner
data = {
    "email": "leigha@looker.com",
    "name": "leighaspartner",
    "type":"Partner"
    }

req = Mock(get_json=Mock(return_value=data), args=data)

# Call tested function
main.form_trigger(req)