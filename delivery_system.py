import datetime
import math
import time
import random
from enum import Enum
from typing import List, Dict, Optional
import uuid



class OrderStatus(Enum):
    INITIATED = "Initiated"
    ACCEPTED = "Accepted"
    READY_FOR_PICKUP = "Ready for Pickup"
    OUT_FOR_DELIVERY = "Out for Delivery"
    DELIVERED = "Delivered"
    REJECTED = "Rejected"


class DeliveryAgentStatus(Enum):
    FREE = "Free"
    BUSY = "Busy"



class Location:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def distance_to(self, other_location) -> float:
        return math.sqrt((self.x - other_location.x) ** 2 + (self.y - other_location.y) ** 2)

    def __str__(self):
        return f"({self.x}, {self.y})"


class Entity:
    def __init__(self, name: str, location: Location):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.location = location


class User(Entity):
    def __init__(self, name: str, location: Location, phone: str, email: str):
        super().__init__(name, location)
        self.phone = phone
        self.email = email
        self.order_history = []

    def place_order(self, restaurant, items: List[Dict], is_priority: bool = False) -> 'Order':
        order = Order(self, restaurant, items, is_priority)
        self.order_history.append(order)
        print(f"\nOrder {order.id} placed by {self.name} at {restaurant.name}")
        return order

    def check_order_status(self, order_id: str) -> None:
        for order in self.order_history:
            if order.id == order_id:
                print(f"\nOrder {order.id} status: {order.status.value}")
                if order.delivery_agent:
                    print(f"Delivery Agent: {order.delivery_agent.name}")
                return
        print(f"Order with ID {order_id} not found in your history")


class Restaurant(Entity):
    def __init__(self, name: str, location: Location, menu: Dict[str, float]):
        super().__init__(name, location)
        self.menu = menu
        self.orders = []
        self.rating = random.uniform(3.0, 5.0)

    def add_order(self, order: 'Order') -> None:
        self.orders.append(order)
        DeliverySystem.instance().add_order(order)

    def accept_order(self, order_id: str) -> None:
        for order in self.orders:
            if order.id == order_id and order.status == OrderStatus.INITIATED:
                order.update_status(OrderStatus.ACCEPTED)
                print(f"\nOrder {order.id} accepted by {self.name}")
                return
        print(f"Order with ID {order_id} not found or not in initiated status")

    def reject_order(self, order_id: str) -> None:
        for order in self.orders:
            if order.id == order_id and order.status == OrderStatus.INITIATED:
                order.update_status(OrderStatus.REJECTED)
                print(f"\nOrder {order.id} rejected by {self.name}")
                return
        print(f"Order with ID {order_id} not found or not in initiated status")

    def mark_order_ready(self, order_id: str) -> None:
        for order in self.orders:
            if order.id == order_id and order.status == OrderStatus.ACCEPTED:
                order.update_status(OrderStatus.READY_FOR_PICKUP)
                DeliverySystem.instance().assign_delivery_agent(order)
                print(f"\nOrder {order.id} is ready for pickup from {self.name}")
                return
        print(f"Order with ID {order_id} not found or not in accepted status")

    def __str__(self):
        return f"{self.name} (Rating: {self.rating:.1f})"

    def display_menu(self):
        print(f"\n--- {self.name} Menu ---")
        for item, price in self.menu.items():
            print(f"{item}: ₹{price:.2f}")


class DeliveryAgent(Entity):
    def __init__(self, name: str, location: Location, phone: str):
        super().__init__(name, location)
        self.phone = phone
        self.status = DeliveryAgentStatus.FREE
        self.current_order = None
        self.rating = random.uniform(4.0, 5.0)

    def assign_order(self, order: 'Order') -> None:
        if self.status == DeliveryAgentStatus.FREE:
            self.status = DeliveryAgentStatus.BUSY
            self.current_order = order
            order.assign_delivery_agent(self)
            print(f"\nDelivery Agent {self.name} assigned to Order {order.id}")

            order.update_status(OrderStatus.OUT_FOR_DELIVERY)
        else:
            print(f"Delivery Agent {self.name} is already busy")

    def complete_delivery(self) -> None:
        if self.current_order:
            self.current_order.update_status(OrderStatus.DELIVERED)
            print(f"\nOrder {self.current_order.id} delivered by {self.name}")
            self.location = self.current_order.user.location  # Update location to customer location
            self.current_order = None
            self.status = DeliveryAgentStatus.FREE

    def __str__(self):
        return f"{self.name} ({self.status.value} - at location {self.location})"


class Order:
    def __init__(self, user: User, restaurant: Restaurant, items: List[Dict], is_priority: bool = False):
        self.id = str(uuid.uuid4())[:8]
        self.user = user
        self.restaurant = restaurant
        self.items = items
        self.status = OrderStatus.INITIATED
        self.is_priority = is_priority
        self.creation_time = datetime.datetime.now()
        self.delivery_agent = None
        self.status_history = [
            {"status": OrderStatus.INITIATED, "time": self.creation_time}
        ]


        self.distance = self.restaurant.location.distance_to(self.user.location)
        self.base_delivery_fee = max(20, round(self.distance * 10))

        self.priority_fee = 0
        if is_priority:
            self.priority_fee = max(50, round(self.base_delivery_fee * 0.5))

        restaurant.add_order(self)

    def update_status(self, new_status: OrderStatus) -> None:
        self.status = new_status
        self.status_history.append({"status": new_status, "time": datetime.datetime.now()})

        if new_status == OrderStatus.DELIVERED:
            self.generate_bill()

    def assign_delivery_agent(self, agent: DeliveryAgent) -> None:
        self.delivery_agent = agent

    def calculate_total_amount(self) -> float:
        item_total = sum(item['price'] * item['quantity'] for item in self.items)
        delivery_fee = self.base_delivery_fee + self.priority_fee
        platform_fee = item_total * 0.07  # 7% platform fee
        gst = item_total * 0.05  # 5% GST
        return item_total + delivery_fee + platform_fee + gst

    def generate_bill(self) -> None:
        item_total = sum(item['price'] * item['quantity'] for item in self.items)
        delivery_time = (self.status_history[-1]["time"] - self.creation_time).total_seconds() / 60

        print("\n" + "=" * 50)
        print(f"BILL FOR ORDER {self.id}")
        print("=" * 50)
        print(f"Customer: {self.user.name}")
        print(f"Restaurant: {self.restaurant.name}")
        print(f"Order Time: {self.creation_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Delivery Time: {self.status_history[-1]['time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Time: {delivery_time:.1f} minutes")
        print("-" * 50)
        print("ITEMS:")
        for item in self.items:
            print(f"  {item['name']} x {item['quantity']}: ₹{item['price'] * item['quantity']:.2f}")
        print("-" * 50)
        print(f"Item Total: ₹{item_total:.2f}")
        print(f"Delivery Fee: ₹{self.base_delivery_fee:.2f}")
        if self.is_priority:
            print(f"Priority Fee: ₹{self.priority_fee:.2f}")
        print(f"Platform Fee (7%): ₹{item_total * 0.07:.2f}")
        print(f"GST (5%): ₹{item_total * 0.05:.2f}")
        print("-" * 50)
        print(f"TOTAL AMOUNT: ₹{self.calculate_total_amount():.2f}")
        print("=" * 50)
        print("Thank you for using our Food Delivery Platform!")
        print("=" * 50)

    def __str__(self):
        priority_str = "PRIORITY " if self.is_priority else ""
        return f"{priority_str}Order {self.id} - Status: {self.status.value}"



class DeliverySystem:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if DeliverySystem._instance is not None:
            raise Exception("DeliverySystem is a singleton class")

        self.pending_orders = []
        self.priority_orders = []
        self.normal_orders = []
        self.delivery_agents = []

    def add_delivery_agent(self, agent: DeliveryAgent) -> None:
        self.delivery_agents.append(agent)

    def add_order(self, order: Order) -> None:
        self.pending_orders.append(order)

    def assign_delivery_agent(self, order: Order) -> None:

        free_agents = [agent for agent in self.delivery_agents if agent.status == DeliveryAgentStatus.FREE]

        if not free_agents:

            if order.is_priority:
                self.priority_orders.append(order)
                print(f"\nNo delivery agents available. Added Order {order.id} to priority queue.")
            else:
                self.normal_orders.append(order)
                print(f"\nNo delivery agents available. Added Order {order.id} to normal queue.")
            return


        closest_agent = min(free_agents, key=lambda agent: agent.location.distance_to(order.restaurant.location))
        closest_agent.assign_order(order)

    def process_pending_orders(self) -> None:
        while self.priority_orders and any(agent.status == DeliveryAgentStatus.FREE for agent in self.delivery_agents):
            order = self.priority_orders.pop(0)
            if order.status == OrderStatus.READY_FOR_PICKUP:
                self.assign_delivery_agent(order)

        while self.normal_orders and any(agent.status == DeliveryAgentStatus.FREE for agent in self.delivery_agents):
            order = self.normal_orders.pop(0)
            if order.status == OrderStatus.READY_FOR_PICKUP:
                self.assign_delivery_agent(order)

    def simulate_deliveries(self) -> None:

        for agent in self.delivery_agents:
            if agent.status == DeliveryAgentStatus.BUSY and agent.current_order:
                # Calculate delivery time based on distance
                distance = agent.location.distance_to(agent.current_order.user.location)
                # For simulation, complete delivery immediately
                agent.complete_delivery()

        self.process_pending_orders()

    def display_system_status(self) -> None:
        print("\n=== SYSTEM STATUS ===")
        print(f"Priority Orders Waiting: {len(self.priority_orders)}")
        print(f"Normal Orders Waiting: {len(self.normal_orders)}")
        print("\nDelivery Agents:")
        for agent in self.delivery_agents:
            print(f"  - {agent}")

class SimulationController:
    def __init__(self):
        self.delivery_system = DeliverySystem.instance()
        self.users = []
        self.restaurants = []
        self.setup_sample_data()

    def setup_sample_data(self) -> None:
        r1 = Restaurant("Spice Delight", Location(10, 15), {
            "Butter Chicken": 250,
            "Paneer Tikka": 220,
            "Dal Makhani": 180,
            "Naan": 40,
            "Biryani": 300
        })

        r2 = Restaurant("Pizza Paradise", Location(5, 8), {
            "Margherita Pizza": 350,
            "Pepperoni Pizza": 450,
            "Garlic Bread": 150,
            "Pasta Alfredo": 280,
            "Cheesy Fries": 180
        })

        r3 = Restaurant("Burger Hub", Location(15, 12), {
            "Classic Burger": 220,
            "Cheese Burger": 260,
            "Fries": 120,
            "Milkshake": 150,
            "Nuggets": 180
        })


        agents = [
            DeliveryAgent("Ravi", Location(8, 10), "9876543210"),
            DeliveryAgent("Priya", Location(12, 8), "9876543211"),
            DeliveryAgent("Amit", Location(6, 15), "9876543212")
        ]

        for agent in agents:
            self.delivery_system.add_delivery_agent(agent)
        u1 = User("Rahul", Location(18, 20), "9876543213", "rahul@example.com")
        u2 = User("Neha", Location(7, 22), "9876543214", "neha@example.com")

        self.users = [u1, u2]

    def run(self) -> None:
        print("\n=== FOOD DELIVERY PLATFORM SIMULATION ===")

        while True:
            print("\nSelect an interface:")
            print("1. Customer Interface")
            print("2. Restaurant Interface")
            print("3. System Status")
            print("4. Simulate Delivery Progress")
            print("5. Exit")

            choice = input("\nEnter your choice (1-5): ")

            if choice == '1':
                self.customer_interface()
            elif choice == '2':
                self.restaurant_interface()
            elif choice == '3':
                self.system_status_interface()
            elif choice == '4':
                self.delivery_system.simulate_deliveries()
            elif choice == '5':
                print("\nExiting simulation. Thank you!")
                break
            else:
                print("\nInvalid choice. Please try again.")

    def customer_interface(self) -> None:
        print("\n=== CUSTOMER INTERFACE ===")
        print("\nAvailable Users:")
        for i, user in enumerate(self.users, 1):
            print(f"{i}. {user.name}")

        user_choice = int(input("\nSelect a user (number): ")) - 1
        if 0 <= user_choice < len(self.users):
            selected_user = self.users[user_choice]

            while True:
                print(f"\nWelcome, {selected_user.name}!")
                print("1. Place an Order")
                print("2. Check Order Status")
                print("3. Back to Main Menu")

                cust_choice = input("\nEnter your choice (1-3): ")

                if cust_choice == '1':
                    self.place_order_interface(selected_user)
                elif cust_choice == '2':
                    order_id = input("\nEnter Order ID: ")
                    selected_user.check_order_status(order_id)
                elif cust_choice == '3':
                    break
                else:
                    print("\nInvalid choice. Please try again.")
        else:
            print("\nInvalid user selection.")

    def place_order_interface(self, user: User) -> None:
        print("\n=== PLACE ORDER ===")

        print("\nAvailable Restaurants:")
        for i, restaurant in enumerate(self.restaurants, 1):
            print(f"{i}. {restaurant}")

        rest_choice = int(input("\nSelect a restaurant (number): ")) - 1
        if 0 <= rest_choice < len(self.restaurants):
            selected_restaurant = self.restaurants[rest_choice]
            selected_restaurant.display_menu()
            items = []
            while True:
                item_name = input("\nEnter item name (or 'done' to finish): ")
                if item_name.lower() == 'done':
                    break

                if item_name in selected_restaurant.menu:
                    quantity = int(input(f"Enter quantity for {item_name}: "))
                    items.append({
                        'name': item_name,
                        'price': selected_restaurant.menu[item_name],
                        'quantity': quantity
                    })
                else:
                    print("Item not found in menu. Please try again.")
            priority_choice = input("\nDo you want priority delivery? (y/n): ")
            is_priority = priority_choice.lower() == 'y'

            if items:
                order = user.place_order(selected_restaurant, items, is_priority)
                print(f"\nOrder placed successfully! Your order ID is: {order.id}")
            else:
                print("\nNo items selected. Order cancelled.")
        else:
            print("\nInvalid restaurant selection.")

    def restaurant_interface(self) -> None:
        print("\n=== RESTAURANT INTERFACE ===")

        # Display available restaurants
        print("\nAvailable Restaurants:")
        for i, restaurant in enumerate(self.restaurants, 1):
            print(f"{i}. {restaurant}")

        rest_choice = int(input("\nSelect a restaurant (number): ")) - 1
        if 0 <= rest_choice < len(self.restaurants):
            selected_restaurant = self.restaurants[rest_choice]

            while True:
                print(f"\nWelcome, {selected_restaurant.name}!")
                print("1. View Pending Orders")
                print("2. Accept/Reject Order")
                print("3. Mark Order as Ready for Pickup")
                print("4. Back to Main Menu")

                rest_action = input("\nEnter your choice (1-4): ")

                if rest_action == '1':
                    pending_orders = [order for order in selected_restaurant.orders
                                      if order.status in [OrderStatus.INITIATED, OrderStatus.ACCEPTED]]

                    if pending_orders:
                        print("\nPending Orders:")
                        for order in pending_orders:
                            print(f"Order {order.id} - Status: {order.status.value}")
                    else:
                        print("\nNo pending orders.")

                elif rest_action == '2':
                    # Accept/Reject an order
                    order_id = input("\nEnter Order ID: ")
                    action = input("Accept (a) or Reject (r) this order? ")

                    if action.lower() == 'a':
                        selected_restaurant.accept_order(order_id)
                    elif action.lower() == 'r':
                        selected_restaurant.reject_order(order_id)
                    else:
                        print("\nInvalid action.")

                elif rest_action == '3':
                    # Mark an order as ready for pickup
                    order_id = input("\nEnter Order ID: ")
                    selected_restaurant.mark_order_ready(order_id)

                elif rest_action == '4':
                    break

                else:
                    print("\nInvalid choice. Please try again.")
        else:
            print("\nInvalid restaurant selection.")

    def system_status_interface(self) -> None:
        self.delivery_system.display_system_status()


if __name__ == "__main__":
    simulation = SimulationController()
    simulation.run()