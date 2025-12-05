import requests
import frappe
from frappe.utils import nowdate
import json
from datetime import datetime
import phonenumbers  
import pycountry


@frappe.whitelist(allow_guest=True)
def send_whatsapp(to_number, message):
    try:
        # Ensure it's a string and strip spaces
        to_number = str(to_number).strip()
        response = send_whatsapp_message(to_number, message)
        return response
    except Exception:
        frappe.throw("Invalid number format.")

# @frappe.whitelist(allow_guest=True)
# def send_whatsapp(to_number, message):
#     try:
#         to_number = int(to_number)
#         response = send_whatsapp_message(to_number, message)
#         return response
#     except ValueError:
#         frappe.throw("Invalid number format.")

@frappe.whitelist(allow_guest=True)
def send_whatsapp_message(to_number, message, country_name=None):
    settings = get_whatsapp_settings()
    API_URL = 'https://waclient.com/api/send'
    ACCESS_TOKEN = settings['access_token']
    INSTANCE_ID = settings['instance_id']

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    # ----------- PHONE NUMBER FORMATTING ----------
    if country_name:
        country_code = get_country_code_from_country_name(country_name)
        if country_code:
            to_number = format_phone_number(to_number, country_code).replace("+", "")
        else:
            frappe.log_error(
                message=f"Failed to get country code for {country_name}",
                title="Country Code Error"
            )
            return {"error": f"Invalid country name: {country_name}"}
    else:
        to_number = "254" + to_number[-9:]

    # ------------ API PAYLOAD -----------
    data = {
        "number": to_number,
        "type": "text",
        "message": message,
        "instance_id": INSTANCE_ID,
        "access_token": ACCESS_TOKEN,
    }

    try:
        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()

        # Convert response to JSON
        resp_json = response.json()

        # Log minimized response
        resp_str = str(resp_json)
        truncated = (resp_str[:137] + "...") if len(resp_str) > 140 else resp_str
        frappe.log_error(truncated, "WhatsApp Text API Response")

        # ------------ Extract status + id from response ------------
        status = resp_json.get("status")
        message_data = resp_json.get("message")  # expect dict

        if isinstance(message_data, dict):
            key_id = message_data.get("key", {}).get("id")
        else:
            frappe.log_error(
                f"Unexpected message format: {message_data}",
                "WhatsApp Text API Error"
            )
            return {"error": "Unexpected message response format"}

        # ------------ Insert into Whatsapp Feedback ------------
        try:
            current_date = nowdate()
            whatsapp_status_doc = frappe.get_doc({
                "doctype": "Whatsapp Feedback",
                "phone_number": to_number,
                "status": status,
                "key_id": key_id,
                "date": current_date,
            })
            whatsapp_status_doc.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                f"Error inserting WhatsApp Feedback: {str(e)}",
                "WhatsApp Text API Error"
            )
            return {"error": "Failed to insert WhatsApp Feedback"}

        return resp_json

    except requests.exceptions.RequestException as e:
        frappe.log_error(message=str(e), title="WhatsApp API Request Error")
        return {"error": str(e)}

    




@frappe.whitelist(allow_guest=True)
def send_whatsapp_buttons(to_number, message_text, buttons, country_name=None):
    """
    Send an interactive WhatsApp message with buttons using WAClient.
    """

    settings = get_whatsapp_settings()
    API_URL = 'https://waclient.com/api/send'
    ACCESS_TOKEN = settings['access_token']
    INSTANCE_ID = settings['instance_id']

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    if country_name:
        country_code = get_country_code_from_country_name(country_name)
        if country_code:
            to_number = format_phone_number(to_number, country_code).replace("+", "")
        else:
            frappe.log_error(message=f"Failed to get country code for {country_name}", title="Country Code Error")
            return {"error": f"Invalid country name: {country_name}"}
    else:
        to_number = "254" + to_number[-9:]

    # Construct interactive message payload
    data = {
        "number": to_number,
        "type": "interactive",
        "instance_id": INSTANCE_ID,
        "access_token": ACCESS_TOKEN,
        "interactive": {
            "type": "button",
            "body": {
                "text": message_text
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"btn_{i+1}",
                            "title": btn
                        }
                    } for i, btn in enumerate(buttons[:3])  # Max 3 buttons
                ]
            }
        }
    }

    try:
        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        frappe.log_error(message=str(e), title="WhatsApp Button API Error")
        return {"error": str(e)}

    


@frappe.whitelist(allow_guest=True)
def send_whatsapp_media(to_number, message, media_url, file_name=None, country_name=None):
    if file_name:
        file_name = f"{file_name}.pdf"

    if country_name:
        country_code = get_country_code_from_country_name(country_name)

        if country_code:
            to_number = format_phone_number(to_number, country_code).replace("+", "")
        else:
            frappe.log_error(message=f"Failed to get country code for {country_name}", title="Country Code Error")
            return {"error": f"Invalid country name: {country_name}"}
    else:
        to_number = "254" + to_number[-9:]

    try:
        to_number = int(to_number)

        response = send_media_file(to_number, message, media_url, file_name)

        response_str = str(response)
        truncated_response = (response_str[:137] + '...') if len(response_str) > 140 else response_str
        frappe.log_error(truncated_response, "WhatsApp Media API Response")

        if isinstance(response, dict):
            status = response.get("status")
            message_response = response.get("message")

            
            if isinstance(message_response, dict):
                id = message_response.get("key", {}).get("id")
            else:
                frappe.log_error(f"Unexpected message response format: {message_response}", "WhatsApp Media API Error")
                return {"error": "Unexpected message response format"}

            
            try:
                current_date = nowdate()
                whatsapp_status_doc = frappe.get_doc({
                    "doctype": "Whatsapp Feedback",
                    "phone_number": to_number,
                    "status": status,
                    "key_id": id,
                    "date": current_date
                })
                whatsapp_status_doc.insert(ignore_permissions=True)
                frappe.db.commit()

            except Exception as e:
                frappe.log_error(f"Error inserting Whatsapp Feedback: {str(e)}", "WhatsApp Media API Error")
                return {"error": "Error inserting WhatsApp Feedback"}

        else:
            frappe.log_error(f"Unexpected response format: {response}", "WhatsApp Media API Error")
            return {"error": "Unexpected response format"}

        return response

    except ValueError:
        frappe.log_error(f"Invalid phone number: {to_number}", "WhatsApp Media API Error")
        return {"error": "Invalid phone number"}

@frappe.whitelist(allow_guest=True)
def send_media_file(to_number, message, media_url, file_name=None):
    settings = get_whatsapp_settings()
    API_URL = 'https://waclient.com/api/send'
    ACCESS_TOKEN = settings['access_token']
    INSTANCE_ID = settings['instance_id']


    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    data = {
        'number': to_number,
        'type': 'media',
        'message': message,
        'media_url': media_url,
        'filename': file_name,
        'instance_id': INSTANCE_ID,
        'access_token': ACCESS_TOKEN
    }
    try:
        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            frappe.log_error(message=response.text, title="WhatsApp API Response Error")
            return {"error": "Response is not in JSON format"}
    except requests.exceptions.RequestException as e:
        frappe.log_error(message=str(e), title="WhatsApp API Request Error")
        return {"error": str(e)}

def get_whatsapp_settings():
    try:
        settings = frappe.get_single("Whatsapp Settings")
        access_token = settings.get('access_token')
        instance_id = settings.get('instance_id')
        return {
            'access_token': access_token,
            'instance_id': instance_id
        }
    except frappe.DoesNotExistError:
        frappe.throw("WhatsApp settings not found.")



@frappe.whitelist(allow_guest=True)
def receive_whatsapp_message():
    try:
        data = frappe.request.get_data(as_text=True)
        data = json.loads(data)

        print(f"\n\n\n {data} \n\n\n")
        message = data['data']["message"]
        instance_id = data["instance_id"]
        event_type = data['data']["event"]
        text = message["body_message"]['messages']['extendedTextMessage']["text"]
        sender_contact = message['from_contact']
        push_name = message['push_name']
        timestamp_str = message['body_message']['messages']['messageContextInfo']['deviceListMetadata']['senderTimestamp']
        timestamp = int(timestamp_str)
        dt_object = datetime.fromtimestamp(timestamp)
        formatted_datetime = dt_object.strftime('%Y-%m-%d %H:%M:%S')

        new_doc = frappe.get_doc({
            "doctype": "Whatsapp Message Receiver",
            "event": event_type,
            "sender": push_name,
            "sender_contact":sender_contact,
            "time_stamp": formatted_datetime,
            "message": text
        })

        new_doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": "Message saved successfully"}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp Message Error")
        return {"status": "error", "message": str(e)}
    

@frappe.whitelist(allow_guest=True)
def set_whatsapp_webhook():
    try:
        settings = frappe.get_single("Whatsapp Settings")
        if settings.check:
            access_token = settings.get('access_token')
            instance_id = settings.get('instance_id')
            base_webhook_url = settings.get('webhook_url')
            method_path=settings.get('method_url')

            if base_webhook_url and access_token and instance_id:
                # method_path = "/api/method/whatsapp_integration.service.rest.receive_whatsapp_message"
                # method_path = "/api/method/doctor_booking.services.rest.receive_whatsapp_message"
                webhook_url = f"{base_webhook_url.rstrip('/')}{method_path}"
                
                api_url = "https://waclient.com/api/set_webhook"
                params = {
                    "webhook_url": webhook_url,
                    "enable": "true",
                    "instance_id": instance_id,
                    "access_token": access_token
                }
                
                response = requests.get(api_url, params=params)
                
                if response.status_code == 200:
                    frappe.msgprint("Webhook set successfully!")
                else:
                    return
    except Exception as e:
        frappe.throw(f"An error occurred: {str(e)}")

@frappe.whitelist(allow_guest=True)
def format_phone_number(local_number, country_code):
    try:
        local_number = local_number.replace(" ", "")

        country_code = country_code.replace("+", "")

        if local_number.startswith("+" + country_code) or local_number.startswith(country_code):
            return local_number.lstrip("+")

        parsed_number = phonenumbers.parse(local_number, country_code)
        formatted_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

        return formatted_number.lstrip("+")
    
    except phonenumbers.NumberParseException:
        frappe.log_error(message=f"Invalid phone number: {local_number}", title="Phone Number Formatting Error")
        return country_code + local_number.lstrip("0")  # Fallback: remove leading zeros and append country code


@frappe.whitelist(allow_guest=True)
def get_country_code_from_number(phone_number):
    try:
        frappe.logger().info(f"Received phone number: {phone_number}")  

        if not isinstance(phone_number, str) or not phone_number.strip():
            frappe.log_error("Empty or invalid phone number input", "Phone Number Parsing Error")
            return {"error": "Invalid phone number format"}

        if not phone_number.startswith("+"):
            phone_number = "+" + phone_number  

        parsed_number = phonenumbers.parse(phone_number, None)
        country_code = f"{parsed_number.country_code}"

        frappe.logger().info(f"Extracted country code: {country_code}")  

        return {"country_code": country_code}

    except phonenumbers.NumberParseException as e:
        frappe.log_error(f"Phone number parsing failed: {str(e)}", "Phone Number Parsing Error")
        return {"error": "Invalid phone number"}


@frappe.whitelist(allow_guest=True)
def get_country_code_from_country_name(country_name):
    try:
        country = pycountry.countries.get(name=country_name)
        if not country:
            frappe.log_error(message=f"Country name not found: {country_name}", title="Invalid Country Name")
            return None

        frappe.log_error(message=f"ISO alpha-2 country code: {country.alpha_2}", title="Country Code Function")

        country_code = phonenumbers.country_code_for_region(country.alpha_2)
        
        frappe.log_error(message=f"Country dial code for {country_name}: {country_code}", title="Country Code Function")

        if country_code:
            return "+" + str(country_code)
        else:
            frappe.log_error(message=f"Country dial code not found for {country_name}", title="Country Code Retrieval Error")
            return None
    except Exception as e:
        frappe.log_error(message=f"Error in getting country dial code for {country_name}: {str(e)}", title="Country Code Retrieval Error")
        return None

@frappe.whitelist(allow_guest=True)
def get_country_codes():
    countries = frappe.get_list("Country", fields=["name"])  
    codes = {}
    
    for country in countries:
        country_code = get_country_code_from_country_name(country.name)  
        if country_code:
            codes[country.name] = country_code 
    
    return codes

    
