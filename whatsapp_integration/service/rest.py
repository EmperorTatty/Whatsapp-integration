import requests
import frappe
import re
from frappe.utils import nowdate, now_datetime
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
        to_number = normalize_whatsapp_number(to_number)
        if not to_number:
            frappe.throw("Invalid number format.")

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

        # Parse JSON
        resp_json = response.json()

        # Minimized log
        resp_str = str(resp_json)
        truncated = (resp_str[:137] + "...") if len(resp_str) > 140 else resp_str
        frappe.log_error(truncated, "WhatsApp Text API Response")

        # ------------ Extract status + id from response ------------
        status = resp_json.get("status")
        message_data = resp_json.get("data")   # FIXED (previously resp_json["message"])

        if not isinstance(message_data, dict):
            frappe.log_error(
                title="WhatsApp Text API Error",
                message=f"Unexpected message format: {message_data}"
            )
            return {"error": "Unexpected message response format"}

        key_id = message_data.get("key", {}).get("id")

        if not key_id:
            frappe.log_error("Missing key_id in response", str(resp_json))

        # ------------ Insert into Whatsapp Feedback ------------
        try:
            whatsapp_status_doc = frappe.get_doc({
                "doctype": "Whatsapp Feedback",
                "phone_number": to_number,
                "status": status,
                "key_id": key_id,
                "date": nowdate(),
            })
            whatsapp_status_doc.insert(ignore_permissions=True)
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(
                title="WhatsApp Text API Error",
                message=f"Error inserting WhatsApp Feedback: {str(e)}"
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
        to_number = normalize_whatsapp_number(to_number)
        if not to_number:
            frappe.log_error(message=f"Invalid number format: {to_number}", title="WhatsApp Button Number Error")
            return {"error": "Invalid number format"}

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
        to_number = normalize_whatsapp_number(to_number)
        if not to_number:
            frappe.log_error(message=f"Invalid number format: {to_number}", title="WhatsApp Media Number Error")
            return {"error": "Invalid phone number"}

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



    if to_number is None:
        return None

    to_number = str(to_number).strip()
    if country_name:
        country_code = get_country_code_from_country_name(country_name)
        if not country_code:
            return None
        try:
            return format_phone_number(to_number, country_code).replace("+", "")
        except Exception:
            return None

    if to_number.startswith("+"):
        return to_number[1:]

    if to_number.startswith("00"):
        return to_number[2:]

    cleaned = re.sub(r"[^0-9]", "", to_number)
    if len(cleaned) == 9:
        return "254" + cleaned
    if len(cleaned) >= 10:
        return cleaned
    return None


def get_whatsapp_sender_contact(payload):
    if not payload:
        return None

    sender = payload.get("from") or payload.get("data", {}).get("message", {}).get("from_contact")
    if sender:
        return str(sender).strip()

    return None


def get_whatsapp_event_type(payload):
    if not payload:
        return None

    event = payload.get("data", {}).get("event") or payload.get("type")
    return event


def extract_whatsapp_order(payload):
    if not payload:
        return None

    order = payload.get("order") or payload.get("data", {}).get("order")
    if not order:
        message = payload.get("data", {}).get("message", {})
        if isinstance(message, dict):
            order = message.get("order") or message.get("extendedTextMessage", {}).get("order")

    if not order or not isinstance(order, dict):
        return None

    product_items = order.get("product_items") or order.get("items") or []
    if not isinstance(product_items, list):
        return None

    items = []
    for product in product_items:
        if not isinstance(product, dict):
            continue
        product_id = product.get("product_retailer_id") or product.get("product_id") or product.get("id")
        qty = product.get("quantity") or product.get("qty") or 1
        if product_id:
            items.append({
                "whatsapp_product_id": str(product_id).strip(),
                "quantity": float(qty) if qty else 1.0
            })

    if not items:
        return None

    customer_phone = payload.get("from") or payload.get("data", {}).get("message", {}).get("from_contact")
    return {
        "customer_phone": customer_phone,
        "order_id": order.get("catalog_id") or order.get("id") or order.get("order_id"),
        "items": items,
    }


def find_or_create_customer_from_phone(phone_number):
    if not phone_number:
        frappe.throw("Customer phone number is required for WhatsApp order processing.")

    normalized_phone = normalize_whatsapp_number(phone_number)
    if not normalized_phone:
        frappe.throw("Unable to normalize customer phone number.")

    customer_name = frappe.db.get_value("Customer", {"mobile_no": normalized_phone}, "name")
    if not customer_name:
        customer_name = frappe.db.get_value("Customer", {"phone": normalized_phone}, "name")

    if customer_name:
        return frappe.get_doc("Customer", customer_name)

    customer_group = frappe.db.get_value("Global Defaults", None, "default_customer_group")
    territory = frappe.db.get_value("Global Defaults", None, "default_territory")
    if not customer_group:
        customer_group = frappe.db.get_value("Customer Group", {"disabled": 0}, "name") or "All Customer Groups"
    if not territory:
        territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"

    customer_doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": f"WhatsApp Customer {normalized_phone[-9:]}",
        "customer_type": "Individual",
        "customer_group": customer_group,
        "territory": territory,
        "mobile_no": normalized_phone,
        "phone": normalized_phone,
    })
    customer_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return customer_doc


def find_item_code_for_whatsapp_product(whatsapp_product_id):
    if not whatsapp_product_id:
        return None

    item_mapping = frappe.get_all(
        "Whatsapp Item Mapping",
        filters={"whatsapp_product_id": whatsapp_product_id},
        fields=["item_code"],
        limit_page_length=1,
    )

    if item_mapping:
        return item_mapping[0].get("item_code")

    if frappe.db.exists("Item", whatsapp_product_id):
        return whatsapp_product_id

    return None


def get_item_rate(item_code):
    if not item_code:
        return 0.0

    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": "Standard Selling"},
        "price_list_rate",
    )
    if price is not None:
        return float(price)

    item = frappe.get_doc("Item", item_code)
    return float(item.get("standard_rate") or item.get("last_purchase_rate") or 0.0)


def get_default_warehouse():
    warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name")
    return warehouse


def create_sales_order_from_whatsapp_order(order_payload):
    if not order_payload or not order_payload.get("items"):
        frappe.throw("WhatsApp order payload did not contain any items.")

    customer = find_or_create_customer_from_phone(order_payload.get("customer_phone"))
    warehouse = get_default_warehouse()
    if not warehouse:
        frappe.throw("No active warehouse found for Sales Order item rows.")

    sales_items = []
    for product in order_payload["items"]:
        item_code = find_item_code_for_whatsapp_product(product["whatsapp_product_id"])
        if not item_code:
            frappe.throw(f"Unable to map WhatsApp product {product['whatsapp_product_id']} to an ERPNext Item.")

        sales_items.append({
            "item_code": item_code,
            "qty": product["quantity"],
            "rate": get_item_rate(item_code),
            "warehouse": warehouse,
        })

    company = frappe.db.get_value("Global Defaults", None, "default_company")
    if not company:
        frappe.throw("Default company is not configured in Global Defaults.")

    sales_order = frappe.get_doc({
        "doctype": "Sales Order",
        "company": company,
        "customer": customer.name,
        "transaction_date": nowdate(),
        "delivery_date": nowdate(),
        "items": sales_items,
    })
    sales_order.insert(ignore_permissions=True)
    frappe.db.commit()
    return sales_order


def save_whatsapp_receiver_message(event_type, sender_contact, message_text):
    receiver_doc = frappe.get_doc({
        "doctype": "Whatsapp Message Receiver",
        "event": event_type,
        "sender": sender_contact or "Unknown",
        "sender_contact": sender_contact,
        "time_stamp": now_datetime(),
        "message": message_text,
    })
    receiver_doc.insert(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def receive_whatsapp_message():
    try:
        data = frappe.request.get_data(as_text=True)
        payload = json.loads(data)

        frappe.logger().info(f"Incoming WhatsApp payload: {json.dumps(payload, indent=2)}")

        event_type = get_whatsapp_event_type(payload) or "unknown"
        sender_contact = get_whatsapp_sender_contact(payload)
        order_payload = extract_whatsapp_order(payload)

        if order_payload:
            sales_order = create_sales_order_from_whatsapp_order(order_payload)
            message_text = f"WhatsApp order received and Sales Order {sales_order.name} created."
            save_whatsapp_receiver_message(event_type, sender_contact, message_text)
            return {
                "status": "success",
                "message": message_text,
                "sales_order": sales_order.name,
            }

        message_text = "Message received successfully."
        if payload.get("data"):
            body_message = payload["data"].get("message", {})
            message_text = body_message.get("conversation") or body_message.get("extendedTextMessage", {}).get("text") or message_text

        save_whatsapp_receiver_message(event_type, sender_contact, message_text)
        return {"status": "success", "message": "Message saved successfully"}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp Message Error")
        return {"status": "error", "message": str(e)}


webhook_receiver = receive_whatsapp_message

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

    
