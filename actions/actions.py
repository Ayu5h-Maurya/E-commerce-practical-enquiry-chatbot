from typing import Any, Text, Dict, List
import os
from dotenv import load_dotenv
import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

load_dotenv()

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")


class ActionTrackOrder(Action):

    def name(self) -> Text:
        return "action_track_order"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        order_id = tracker.get_slot("order_id")

        if not order_id:
            dispatcher.utter_message(text="I could not find your order ID. Please enter it again.")
            return []

        try:
            response = requests.get(
                f"{BACKEND_BASE_URL}/orders/{order_id}",
                timeout=5
            )

            data = response.json()

            if not data.get("found"):
                dispatcher.utter_message(
                    text=f"I could not find any order with ID {order_id}. Please check the order ID and try again."
                )
                return []

            status = data.get("status")
            expected_delivery = data.get("expected_delivery")

            dispatcher.utter_message(
                text=f"Your order {order_id} is currently {status}. Expected delivery: {expected_delivery}."
            )

        except requests.exceptions.RequestException:
            dispatcher.utter_message(
                text="Sorry, I am unable to connect to the order system right now. Please try again later."
            )

        return []


class ActionSubmitComplaint(Action):

    def name(self) -> Text:
        return "action_submit_complaint"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        order_id = tracker.get_slot("order_id")
        issue_description = tracker.get_slot("issue_description")

        if not order_id or not issue_description:
            dispatcher.utter_message(
                text="I could not collect all complaint details. Please try again."
            )
            return []

        try:
            response = requests.post(
                f"{BACKEND_BASE_URL}/complaints",
                json={
                    "order_id": order_id,
                    "issue_description": issue_description
                },
                timeout=5
            )

            data = response.json()

            if data.get("created"):
                ticket_id = data.get("ticket_id")
                dispatcher.utter_message(
                    text=f"Your complaint has been registered successfully. Your ticket ID is {ticket_id}."
                )
            else:
                dispatcher.utter_message(
                    text="Sorry, I could not register your complaint right now."
                )

        except requests.exceptions.RequestException:
            dispatcher.utter_message(
                text="Sorry, I am unable to connect to the complaint system right now. Please try again later."
            )

        return []


class ActionCheckComplaintStatus(Action):

    def name(self) -> Text:
        return "action_check_complaint_status"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        ticket_id = tracker.get_slot("ticket_id")

        if not ticket_id:
            latest_text = tracker.latest_message.get("text")
            if latest_text and latest_text.upper().startswith("TICKET-"):
                ticket_id = latest_text.upper().strip()

        if not ticket_id:
            dispatcher.utter_message(
                text="I could not find your ticket ID. Please enter it again."
            )
            return []

        try:
            response = requests.get(
                f"{BACKEND_BASE_URL}/complaints/{ticket_id}",
                timeout=5
            )

            data = response.json()

            if not data.get("found"):
                dispatcher.utter_message(
                    text=f"I could not find any complaint with ticket ID {ticket_id}. Please check the ticket ID and try again."
                )
                return []

            complaint = data.get("complaint")
            status = complaint.get("status")
            order_id = complaint.get("order_id")
            issue_description = complaint.get("issue_description")

            dispatcher.utter_message(
                text=f"Your complaint {ticket_id} for order {order_id} is currently {status}. Issue: {issue_description}"
            )

        except requests.exceptions.RequestException:
            dispatcher.utter_message(
                text="Sorry, I am unable to connect to the complaint system right now. Please try again later."
            )

        return []
    
class ActionProductEnquiry(Action):

    def name(self) -> Text:
        return "action_product_enquiry"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        latest_text = tracker.latest_message.get("text", "").lower().strip()

        known_products = [
            "wireless mouse",
            "mechanical keyboard",
            "usb c cable",
            "laptop stand"
        ]

        product_name = None

        for product in known_products:
            if product in latest_text:
                product_name = product
                break

        if not product_name:
            dispatcher.utter_message(
                text="Which product are you looking for?"
            )
            return [SlotSet("product_name", None)]

        try:
            response = requests.get(
                f"{BACKEND_BASE_URL}/products/search",
                params={"q": product_name},
                timeout=5
            )

            data = response.json()

            if not data.get("found"):
                dispatcher.utter_message(
                    text=f"Sorry, I could not find {product_name} in our catalog."
                )
                return [SlotSet("product_name", None)]

            product = data.get("product")
            name = product.get("name")
            price = product.get("price")
            stock = product.get("stock")
            category = product.get("category")

            if stock > 0:
                dispatcher.utter_message(
                    text=f"Yes, {name.title()} is available. Price: ₹{price}. Stock: {stock} units. Category: {category}."
                )
            else:
                dispatcher.utter_message(
                    text=f"{name.title()} is currently out of stock. Price: ₹{price}. Category: {category}."
                )

        except requests.exceptions.RequestException:
            dispatcher.utter_message(
                text="Sorry, I am unable to connect to the product system right now. Please try again later."
            )

        return [SlotSet("product_name", None)]
    
class ActionClearReturnSlots(Action):

    def name(self) -> Text:
        return "action_clear_return_slots"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        return [
            SlotSet("order_id", None),
            SlotSet("return_reason", None)
        ]


class ActionSubmitReturnRequest(Action):

    def name(self) -> Text:
        return "action_submit_return_request"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        order_id = tracker.get_slot("order_id")
        return_reason = tracker.get_slot("return_reason")

        if not order_id or not return_reason:
            dispatcher.utter_message(
                text="I could not collect all return details. Please try again."
            )
            return [
                SlotSet("order_id", None),
                SlotSet("return_reason", None)
            ]

        try:
            response = requests.post(
                f"{BACKEND_BASE_URL}/returns",
                json={
                    "order_id": order_id,
                    "reason": return_reason
                },
                timeout=5
            )

            data = response.json()

            if data.get("created"):
                return_id = data.get("return_id")
                dispatcher.utter_message(
                    text=f"Your return/refund request has been created successfully. Your return ID is {return_id}."
                )
            else:
                dispatcher.utter_message(
                    text="Sorry, I could not create your return/refund request right now."
                )

        except requests.exceptions.RequestException:
            dispatcher.utter_message(
                text="Sorry, I am unable to connect to the return system right now. Please try again later."
            )

        return [
            SlotSet("order_id", None),
            SlotSet("return_reason", None)
        ]
        
class ActionCheckReturnStatus(Action):

    def name(self) -> Text:
        return "action_check_return_status"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        return_id = tracker.get_slot("return_id")

        if not return_id:
            latest_text = tracker.latest_message.get("text", "")
            if latest_text and latest_text.upper().startswith("RETURN-"):
                return_id = latest_text.upper().strip()

        if not return_id:
            dispatcher.utter_message(
                text="I could not find your return/refund ID. Please enter it again."
            )
            return []

        try:
            response = requests.get(
                f"{BACKEND_BASE_URL}/returns/{return_id}",
                timeout=5
            )

            data = response.json()

            if not data.get("found"):
                dispatcher.utter_message(
                    text=f"I could not find any return/refund request with ID {return_id}. Please check the ID and try again."
                )
                return [SlotSet("return_id", None)]

            return_request = data.get("return_request")
            order_id = return_request.get("order_id")
            reason = return_request.get("reason")
            status = return_request.get("status")

            dispatcher.utter_message(
                text=f"Your return/refund request {return_id} for order {order_id} is currently {status}. Reason: {reason}"
            )

        except requests.exceptions.RequestException:
            dispatcher.utter_message(
                text="Sorry, I am unable to connect to the return system right now. Please try again later."
            )

        return [SlotSet("return_id", None)]