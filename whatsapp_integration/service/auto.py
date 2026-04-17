import frappe
import json
import requests
from datetime import datetime
import time
from whatsapp_integration.service.rest import send_whatsapp_message

@frappe.whitelist(allow_guest=True)
def handle_incoming_message():
    try:
        # Parse the incoming request
        raw_data = frappe.request.get_data(as_text=True)
        data = json.loads(raw_data)

        print(f"\n\n\n {data} \n\n\n")
        frappe.logger().info(f"Incoming WhatsApp message: {json.dumps(data, indent=2)}")

        instance_id = data.get("instance_id")
        event_type = data["data"].get("event")
        message_data = data["data"].get("message", {})

        # Extract body message
        body_message = message_data.get("body_message", {})
        message_payload = body_message.get("messages", {})

        # Extract text from extendedTextMessage or fallback to conversation
        text = ""
        if "extendedTextMessage" in message_payload:
            text = message_payload["extendedTextMessage"].get("text", "").strip()
        else:
            text = message_payload.get("conversation", "").strip()

        # Extract sender info
        sender_contact = message_data.get("from_contact")
        push_name = message_data.get("push_name", "Unknown")

        # Timestamp
        timestamp_str = message_payload.get("messageContextInfo", {}).get("deviceListMetadata", {}).get("senderTimestamp")
        timestamp = int(timestamp_str) if timestamp_str else int(time.time())
        formatted_datetime = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # Save incoming message
        if event_type == 'received_message':
            new_doc = frappe.get_doc({
                "doctype": "Whatsapp Message Receiver",
                "event": event_type,
                "sender": push_name,
                "sender_contact": sender_contact,
                "time_stamp": formatted_datetime,
                "message": text
            })
            new_doc.insert(ignore_permissions=True)
            frappe.db.commit()

        # Default response
        response = "Thanks for your message! Our team will get back to you shortly."

        # Session tracking key
        session_key = f"whatsapp_last_hello_{sender_contact}"
        said_hello = frappe.cache().get_value(session_key)

        # Respond to "hello"
        if text.lower() == "hello":
            response = (
                "Hi there! 👋 Kindly choose your age bracket:\n"
                "1. Below 30\n"
                "2. 30 - 40\n"
                "3. Above 40\n\n"
                "Reply with the number of your choice."
            )
            # Save session
            frappe.cache().set_value(session_key, "true")

        elif text in ["1", "2", "3"]:
            if said_hello:
                if text == "1":
                    response = "You're probably below 30 years old. 😄"
                elif text == "2":
                    response = "You're likely between 30 and 40 years old. 👍"
                elif text == "3":
                    response = "You're probably above 40 years old. 🎉"
                # Clear session after reply
                frappe.cache().delete_value(session_key)
            else:
                response = "Please say 'hello' first to begin the process."

        elif text.isdigit() and int(text) > 3:
            response = "That's not a valid option. Please reply with 1, 2, or 3."

        elif "hours" in text.lower():
            response = "Our working hours are Mon–Fri, 8am to 5pm."

        elif "price" in text.lower():
            response = "Please specify the item you're interested in so we can share the price."

        # Send reply
        if event_type == 'received_message':
            send_msg(sender_contact, response)

        return {"status": "success", "reply": response}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WAClient AutoResponder Error")
        return {"status": "error", "message": str(e)}




@frappe.whitelist(allow_guest=True)
def send_msg( number, message):
    try:
        settings = frappe.get_doc("Whatsapp Settings")
        api_url = "https://waclient.com/api/send"
        params = {
            "number": number,
            "type": "text",
            "message": message,
            "instance_id": settings.instance_id,
            "access_token": settings.access_token
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json"
        }

        r = requests.get(api_url, params=params, headers=headers)

        frappe.logger().info(f"WhatsApp API response: {r.status_code} {r.text}")

        return {
            "status": "success",
            "response_code": r.status_code,
            "response_body": r.text
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WAClient Send Message Error")
        return {
            "status": "error",
            "message": str(e)
        }



@frappe.whitelist(allow_guest = True)
def send_options(number):
    message = (
        "In which age bracket are you?\n"
        "1. Below 30\n"
        "2. 30 - 40\n"
        "3. Above 40\n\n"
        "Reply with the number of your choice."
    )
    send_whatsapp_message(number, message)

