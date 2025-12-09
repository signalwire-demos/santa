#!/usr/bin/env python3
"""
Santa AI - Interactive Gift Selection Assistant
Powered by SignalWire and RapidAPI
"""

import random
import os
import time
import requests
from pathlib import Path
from typing import Dict, List
from signalwire_agents import AgentBase, AgentServer
from signalwire_agents.core.function_result import SwaigFunctionResult
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import JSONResponse

# Load environment variables
load_dotenv()

HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# Store the SWML handler info for reuse
swml_handler_info = {"id": None, "address_id": None, "address": None}

class SantaAIAgent(AgentBase):
    """Santa Claus - Your Christmas Gift Selection Assistant"""

    def __init__(self):
        super().__init__(
            name="Santa",
            route="/santa",
            record_call=True
        )

        # RapidAPI configuration
        self.rapidapi_key = os.getenv('RAPIDAPI_KEY')
        self.rapidapi_host = os.getenv('RAPIDAPI_HOST', 'real-time-amazon-data.p.rapidapi.com')

        # Gift price limits
        self.min_price = float(os.getenv('MIN_GIFT_PRICE', '10.00'))
        self.max_price = float(os.getenv('MAX_GIFT_PRICE', '100.00'))

        # Christmas year
        self.christmas_year = os.getenv('CHRISTMAS_YEAR', '2025')

        # Initialize conversation prompts
        self._initialize_prompts()

        # Set up SWAIG functions
        self._setup_functions()

    def _initialize_prompts(self):
        """Initialize Santa's personality and conversation prompts"""

        # Santa's personality
        self.prompt_add_section(
            "Personality",
            """You are Santa Claus, speaking directly to a child who has called you at the North Pole.
            You're jolly, warm, and magical. You love to hear what children want for Christmas and help them
            choose the perfect gift. Use phrases like "Ho ho ho!", "Merry Christmas!", and refer to your
            workshop, elves, and reindeer. Keep responses cheerful but concise - remember you're having
            a phone conversation with an excited child."""
        )

        # Conversation states
        self.prompt_add_section(
            "Conversation Flow",
            """Follow these conversation states:

            1. GREETING: Welcome the child warmly, ask their name, and find out what they'd like for Christmas
            2. COLLECTING_WISHES: Listen to what gifts they're interested in, ask clarifying questions if needed
            3. SEARCHING_GIFTS: Let them know you're checking your workshop and Amazon's catalog
            4. PRESENTING_OPTIONS: Present up to 3 gift options enthusiastically
            5. CONFIRMING_SELECTION: Help them choose ONE gift (gently explain they can only pick one)
            6. SENDING_GIFT: Confirm you'll send the gift details to their parents

            Always maintain the magic of Christmas and never break character."""
        )

        # Natural filler words for realistic speech
        self.prompt_add_section(
            "Speech Patterns",
            """Use natural speech patterns including:
            - "Ho ho ho!" when greeting or expressing joy
            - "Let me check my list..." when searching
            - "Oh my!" when surprised
            - "Wonderful choice!" when they select something
            - "The elves will love making this!" when confirming

            Add natural pauses with filler words like "hmm", "let's see", "ah yes" to sound more natural."""
        )

        # Available Tools section - CRITICAL for the AI to use functions
        self.prompt_add_section(
            "Available Tools",
            """You have access to these magical tools to help children:

            1. search_gifts - Use this when a child tells you what they want for Christmas.
               This searches both Santa's workshop and Amazon's catalog.
               Example: If a child says "I want Legos", use search_gifts with query="lego sets"

            2. select_gift - Use this after presenting options to confirm which gift they chose.
               This records their selection and shows it on the screen.

            3. check_nice_list - Use this when a child asks if they're on the nice list or
               when you want to check their behavior status. Always use their name.

            IMPORTANT: You MUST use these tools during the conversation!
            - When a child mentions what they want → use search_gifts
            - After they pick from options → use select_gift
            - When checking nice list → use check_nice_list"""
        )

    def _setup_functions(self):
        """Set up SWAIG functions for gift selection"""

        # Helper functions for state management (following holyguacamole pattern)
        def get_gift_state(raw_data):
            """Get current gift state from global data"""
            global_data = raw_data.get('global_data', {})
            default_state = {
                'gift_search_results': [],
                'selected_gift': None,
                'search_query': '',
                'state': 'greeting'
            }
            return global_data.get('gift_state', default_state), global_data

        def save_gift_state(result, gift_state, global_data):
            """Save gift state to global data (following holyguacamole pattern)"""
            global_data['gift_state'] = gift_state
            result.update_global_data(global_data)
            return result

        @self.tool(
            name="search_gifts",
            description="Search for gift ideas based on what the child wants",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'lego sets', 'dolls', 'video games for kids')"
                    },
                    "child_age": {
                        "type": "integer",
                        "description": "Approximate age of the child (optional)",
                        "minimum": 3,
                        "maximum": 16
                    }
                },
                "required": ["query"]
            }
        )
        def search_gifts(args, raw_data):
            """Search Amazon for gift ideas using RapidAPI"""
            query = args.get('query')
            child_age = args.get('child_age')

            # Send searching event immediately to reset UI
            early_result = SwaigFunctionResult("")
            early_result.swml_user_event({
                'type': 'searching',
                'query': query
            })

            # Get current state
            gift_state, global_data = get_gift_state(raw_data)

            # Don't add "for kids" - use the query as-is
            # The user will specify if they want kids items

            # Debug the search
            print(f"DEBUG SWAIG: search_gifts called with query='{query}', age={child_age}")

            # Call RapidAPI
            products = self._search_amazon_products(query)

            if not products:
                print("DEBUG SWAIG: No products returned from search")
                result = SwaigFunctionResult("Oh dear! I'm having trouble reaching my workshop catalog right now. Let me check again... Can you tell me more about what kind of gift you're looking for?")

                # Update gift state
                gift_state['gift_search_results'] = []
                gift_state['search_query'] = query
                gift_state['state'] = 'search_failed'
                save_gift_state(result, gift_state, global_data)

                # Send event to frontend using swml_user_event (Option A)
                result.swml_user_event({
                    'type': 'search_failed',  # Changed from 'event_type' to match holyguacamole
                    'query': query
                })

                # Debug dump the complete result
                print("\n=== SWAIG RESULT DUMP (search_gifts - FAILED) ===")
                print(f"Response Text: Search failed message")
                print(f"Query: {query}")
                print(f"Event Sent: search_failed")
                print("=== END RESULT DUMP ===\n")

                return result

            # Store results in session
            gift_data = []
            response_text = "Ho ho ho! I found some wonderful gifts that would be perfect! Let me tell you about each one:\n\n"

            for i, product in enumerate(products[:4], 1):
                # Build gift data for frontend
                gift_item = {
                    'id': i,
                    'title': product.get('title', 'Mystery Gift'),
                    'price': product.get('price', 'Price upon request'),
                    'image': product.get('image', ''),
                    'url': product.get('url', ''),
                    'description': product.get('description', '')[:200] if product.get('description') else f"{product.get('title', 'Gift')} - Perfect for children!",
                    'rating': product.get('rating', ''),
                    'asin': product.get('asin', '')
                }
                gift_data.append(gift_item)

                # Build detailed response for the LLM to speak about each product
                response_text += f"Option {i}: {gift_item['title']}\n"
                response_text += f"   Price: {gift_item['price']}\n"

                if gift_item.get('rating'):
                    response_text += f"   Rating: {gift_item['rating']} stars\n"

                if gift_item.get('description'):
                    response_text += f"   Description: {gift_item['description'][:100]}...\n"

                response_text += "\n"

            response_text += "I can see all these wonderful gifts on my magical display here at the North Pole! "
            response_text += "Which one would you like? Just tell me the number - option 1, 2, 3, or 4!"

            print(f"DEBUG SWAIG: Found {len(gift_data)} gifts, sending to frontend")
            print(f"DEBUG SWAIG: Gift data being sent: {[g['title'] for g in gift_data]}")
            print(f"DEBUG SWAIG: Full response text for LLM:\n{response_text}")

            # Create the result with the detailed response text for the LLM
            result = SwaigFunctionResult(response_text)

            # Update gift state
            gift_state['gift_search_results'] = gift_data
            gift_state['search_query'] = query
            gift_state['state'] = 'presenting_options'
            save_gift_state(result, gift_state, global_data)

            # Change to presenting_options step
            result.swml_change_step("presenting_options")

            # Send to frontend using swml_user_event (Option A)
            print(f"DEBUG SWAIG: Sending user_event with {len(gift_data)} gifts to UI")
            result.swml_user_event({
                'type': 'gifts_found',  # Changed from 'event_type' to match holyguacamole
                'gifts': gift_data,
                'query': query
            })

            print("DEBUG SWAIG: COMPLETE DATA BEING RETURNED TO LLM:")
            print(f"  - Response text length: {len(response_text)} chars")
            print(f"  - Global data stored: gift_search_results with {len(gift_data)} items")
            print(f"  - User event sent: gifts_found with product details")

            # Debug dump the complete result
            print("\n=== SWAIG RESULT DUMP (search_gifts) ===")
            print(f"Response Text:\n{response_text}")
            print(f"Global Data: {gift_data}")
            print("=== END RESULT DUMP ===\n")

            return result

        @self.tool(
            name="select_gift",
            description="Select a specific gift from the search results",
            parameters={
                "type": "object",
                "properties": {
                    "gift_choice": {
                        "type": "integer",
                        "description": "The option number (1, 2, 3, or 4)",
                        "minimum": 1,
                        "maximum": 4
                    }
                },
                "required": ["gift_choice"]
            }
        )
        def select_gift(args, raw_data):
            """Confirm the child's gift selection"""
            choice = args.get('gift_choice')

            print(f"DEBUG SWAIG: select_gift called with choice={choice}")

            # Get current state
            gift_state, global_data = get_gift_state(raw_data)
            gift_results = gift_state.get('gift_search_results', [])

            print(f"DEBUG SWAIG: Available gifts in session: {[g.get('title', 'Unknown') for g in gift_results]}")

            if not gift_results:
                print("DEBUG SWAIG: No gift results in session")
                return SwaigFunctionResult("Oh my! I need to search for gifts first. What kind of gift would you like for Christmas?")

            if choice > len(gift_results) or choice < 1:
                print(f"DEBUG SWAIG: Invalid choice {choice}, valid range is 1-{len(gift_results)}")
                return SwaigFunctionResult(f"Oh my! I don't see option {choice}. Please choose from options 1 to {len(gift_results)}. Which one would you like?")

            selected_gift = gift_results[choice - 1]

            print(f"DEBUG SWAIG: Gift selected: {selected_gift['title']} at {selected_gift.get('price', 'N/A')}")

            # Provide complete details for the LLM to speak about the selection
            response_text = f"Ho ho ho! What a wonderful choice! You've selected:\n\n"
            response_text += f"**{selected_gift['title']}**\n"
            response_text += f"Price: {selected_gift.get('price', 'Check listing')}\n"

            if selected_gift.get('rating'):
                response_text += f"Rating: {selected_gift['rating']} stars - Other children love this!\n"

            if selected_gift.get('description'):
                response_text += f"\nThis gift is perfect because: {selected_gift['description'][:150]}\n"

            response_text += "\nThe elves are already preparing this special gift for you! "
            response_text += "I can see it appearing on my list right now. "
            response_text += "\nWould you like to search for anything else from Santa's workshop?"

            result = SwaigFunctionResult(response_text)

            # Update gift state
            gift_state['selected_gift'] = selected_gift
            gift_state['state'] = 'gift_confirmed'
            # Keep the search results for reference
            save_gift_state(result, gift_state, global_data)

            # Change to gift_confirmed step
            result.swml_change_step("gift_confirmed")

            # Send to frontend using swml_user_event (Option A)
            print(f"DEBUG SWAIG: Sending gift_selected event to UI with gift id={choice}")
            result.swml_user_event({
                'type': 'gift_selected',  # Changed from 'event_type' to match holyguacamole
                'gift': selected_gift
            })

            # Debug dump the complete result
            print("\n=== SWAIG RESULT DUMP (select_gift) ===")
            print(f"Response Text:\n{response_text}")
            print(f"Selected Gift: {selected_gift}")
            print(f"Session Data Stored: selected_gift, state='gift_confirmed'")
            print("=== END RESULT DUMP ===\n")

            return result

        @self.tool(
            name="check_nice_list",
            description="Check if a child is on the nice list",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The child's name"
                    }
                },
                "required": ["name"]
            }
        )
        def check_nice_list(args, raw_data):
            """Fun function to check if child is on the nice list"""
            name = args.get('name', 'dear child')

            print(f"DEBUG SWAIG: Checking nice list for: {name}")

            # Get current state
            gift_state, global_data = get_gift_state(raw_data)

            # Always positive and encouraging!
            responses = [
                f"Let me check my big magical book here at the North Pole... *pages rustling*... Oh yes! I found it! {name} is definitely on the NICE LIST! You've been wonderful this year!",
                f"Ho ho ho! {name}! Let me see... *checking list twice*... YES! You're on my nice list! I can see all the kind things you've done this year!",
                f"My special list says {name} has been absolutely wonderful! The elves have been telling me such good things about you! Keep up the fantastic work!",
                f"The elves are so excited! They just told me that {name} is on the nice list! They've been watching and you've been so good!"
            ]

            response_text = random.choice(responses)
            response_text += f"\n\n✨ {name} - NICE LIST STATUS: CONFIRMED! ✨"
            response_text += "\n\nYou're going to have a magical Christmas!"

            result = SwaigFunctionResult(response_text)

            # Update state to show nice list was checked
            gift_state['nice_list_checked'] = True
            gift_state['child_name'] = name
            save_gift_state(result, gift_state, global_data)

            # Send fun animation to frontend using swml_user_event (Option A)
            result.swml_user_event({
                'type': 'nice_list_checked',  # Changed from 'event_type' to match holyguacamole
                'name': name,
                'status': 'nice'
            })

            # Debug dump the complete result
            print("\n=== SWAIG RESULT DUMP (check_nice_list) ===")
            print(f"Response Text:\n{response_text}")
            print(f"Name Checked: {name}")
            print(f"Event Sent: nice_list_checked")
            print("=== END RESULT DUMP ===\n")

            return result

    def _search_amazon_products(self, query: str) -> List[Dict]:
        """Search Amazon products using RapidAPI"""

        if not self.rapidapi_key:
            print("Warning: RapidAPI key not configured")
            return self._get_mock_products(query)

        url = 'https://real-time-amazon-data.p.rapidapi.com/search'

        # Use lowercase headers with x- prefix as shown in the curl example
        headers = {
            'x-rapidapi-host': 'real-time-amazon-data.p.rapidapi.com',
            'x-rapidapi-key': self.rapidapi_key
        }

        # Match the exact query parameters from the curl example
        params = {
            'query': query,
            'page': '1',
            'country': 'US',
            'sort_by': 'RELEVANCE',
            'product_condition': 'ALL',
            'is_prime': 'false',
            'deals_and_discounts': 'NONE'
        }

        try:
            print(f"DEBUG: RapidAPI Search Query: '{query}'")
            print(f"DEBUG: Request URL: {url}")
            print(f"DEBUG: Request params: {params}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            print(f"DEBUG: RapidAPI Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                products = []

                # Debug: Print the structure of the response
                print(f"DEBUG: Response keys: {data.keys()}")

                # The API returns data in data.products array
                product_list = data.get('data', {}).get('products', [])

                print(f"DEBUG: Found {len(product_list)} products from Amazon")

                # Debug: Print first product structure if available
                if product_list:
                    print(f"DEBUG: First product keys: {product_list[0].keys()}")

                for item in product_list[:10]:  # Check more items to find suitable ones
                    # Extract product details
                    title = item.get('product_title', '')
                    price_str = item.get('product_price', '')
                    image = item.get('product_photo', '')
                    url = item.get('product_url', '')
                    asin = item.get('asin', '')
                    rating = item.get('product_star_rating', '')

                    # Skip if no title or image
                    if not title or not image:
                        continue

                    # Try to extract numeric price for filtering
                    try:
                        if price_str and '$' in price_str:
                            # Extract price (e.g., "$29.99" -> 29.99)
                            price_num = float(price_str.replace('$', '').replace(',', '').split()[0])

                            # Skip if outside price range
                            if price_num < self.min_price or price_num > self.max_price:
                                continue
                    except:
                        # Include items even if we can't parse the price
                        pass

                    product_data = {
                        'title': title,
                        'price': price_str or 'Price not available',
                        'image': image,
                        'url': url or f'https://www.amazon.com/dp/{asin}' if asin else '#',
                        'description': item.get('product_description', '')[:200] if item.get('product_description') else f"{title} - Great gift for kids!",
                        'rating': rating,
                        'asin': asin
                    }

                    products.append(product_data)

                    # Debug log the product being added
                    print(f"DEBUG: Added product #{len(products)}: {title[:50]}... Price: {price_str}, Has Image: {bool(image)}")

                    # Stop when we have 3 suitable products
                    if len(products) >= 3:
                        break

                print(f"DEBUG: Returning {len(products)} products after filtering")

                # Debug log the final products
                for i, prod in enumerate(products, 1):
                    print(f"DEBUG: Product {i}: {prod['title'][:50]}... | ${prod['price']} | Image: {bool(prod['image'])}")

                return products[:3]
            else:
                print(f"RapidAPI Error Response: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Request error searching Amazon: {e}")
        except Exception as e:
            print(f"Error parsing Amazon response: {e}")

        # Return mock data if API fails
        return self._get_mock_products(query)

    def _get_mock_products(self, query: str) -> List[Dict]:
        """Return mock products for testing when API is unavailable"""

        mock_products = {
            "lego": [
                {
                    'title': 'LEGO Classic Creative Bricks Set',
                    'price': '$29.99',
                    'image': 'https://via.placeholder.com/300x300?text=LEGO+Set',
                    'url': '#',
                    'description': 'Build anything you can imagine with this classic LEGO set!'
                },
                {
                    'title': 'LEGO City Police Station',
                    'price': '$79.99',
                    'image': 'https://via.placeholder.com/300x300?text=Police+Station',
                    'url': '#',
                    'description': 'Complete police station with vehicles and minifigures'
                },
                {
                    'title': 'LEGO Friends Heartlake City',
                    'price': '$49.99',
                    'image': 'https://via.placeholder.com/300x300?text=LEGO+Friends',
                    'url': '#',
                    'description': 'Build and play in Heartlake City with friends'
                }
            ],
            "doll": [
                {
                    'title': 'American Girl Doll - Holiday Edition',
                    'price': '$98.00',
                    'image': 'https://via.placeholder.com/300x300?text=American+Girl',
                    'url': '#',
                    'description': 'Beautiful holiday-themed American Girl doll'
                },
                {
                    'title': 'Barbie Dreamhouse Playset',
                    'price': '$89.99',
                    'image': 'https://via.placeholder.com/300x300?text=Barbie+Dreamhouse',
                    'url': '#',
                    'description': 'Three-story Barbie dreamhouse with elevator'
                },
                {
                    'title': 'Baby Alive Doll',
                    'price': '$34.99',
                    'image': 'https://via.placeholder.com/300x300?text=Baby+Alive',
                    'url': '#',
                    'description': 'Interactive baby doll that eats, drinks, and more'
                }
            ]
        }

        # Return relevant mock products based on query
        query_lower = query.lower()
        for key, products in mock_products.items():
            if key in query_lower:
                return products

        # Default mock products
        return [
            {
                'title': f'Wonderful {query.title()}',
                'price': '$49.99',
                'image': 'https://via.placeholder.com/300x300?text=Gift',
                'url': '#',
                'description': f'A perfect {query} for Christmas!'
            }
        ]


    def on_swml_request(self, request_data: Dict, callback_path: str, request=None) -> Dict:
        """Handle incoming SWML requests and configure the AI agent"""

        # Detect host from request for video URLs
        host = "localhost:5000"
        protocol = "http"

        if request:
            # Try to get the host from headers
            headers = {k.lower(): v for k, v in request.headers.items()}
            host = headers.get('host', host)

            # Check if we're behind a proxy with x-forwarded-proto
            protocol = headers.get('x-forwarded-proto', 'https')

            # Override protocol for local development
            if 'localhost' in host or '127.0.0.1' in host:
                protocol = 'http'

        # Set video URLs using set_param (this is what makes video work!)
        if host:
            base_url = f"{protocol}://{host}"
            self.set_param("video_idle_file", f"{base_url}/santa_idle.mp4")
            self.set_param("video_talking_file", f"{base_url}/santa_talking.mp4")
            # Add background music for festive atmosphere
            self.set_param("background_file", f"{base_url}/background.mp3")
            self.set_param("background_file_volume", -10)
            print(f"Set video URLs to use host: {base_url}")
        else:
            # Fallback to environment variables or defaults
            video_idle = os.getenv('VIDEO_IDLE_URL', f"{protocol}://{host}/santa_idle.mp4")
            video_talking = os.getenv('VIDEO_TALKING_URL', f"{protocol}://{host}/santa_talking.mp4")
            self.set_param("video_idle_file", video_idle)
            self.set_param("video_talking_file", video_talking)
            # Add background music for festive atmosphere
            self.set_param("background_file", f"{protocol}://{host}/background.mp3")
            self.set_param("background_file_volume", -10)

        # Configure Santa voice as part of language settings (like holyguacamole)
        voice_id = 'uDsPstFWFBUXjIBimV7s'  # Santa voice from SignalWire guide
        self.add_language(
            name="English",
            code="en-US",
            voice=f"elevenlabs.{voice_id}"
        )

        # Optional post-prompt URL from environment
        post_prompt_url = os.environ.get("POST_PROMPT_URL")
        if post_prompt_url:
            self.set_post_prompt("Summarize the conversation, including all the gifts discussed, the child's preferences, their selected gift if any, and any special mentions about their Christmas wishes.")
            self.set_post_prompt_url(post_prompt_url)

        # Add speech hints for better recognition of holiday terms
        self.add_hints([
            "toy", "toys", "game", "games", "doll", "dolls",
            "lego", "puzzle", "bicycle", "bike", "scooter",
            "christmas", "present", "gift", "santa", "elves",
            "nice", "naughty", "list", "workshop", "north pole",
            "yes", "no", "please", "thank you",
            "option one", "option two", "option three",
            "first", "second", "third"
        ])

        # Call parent implementation to handle the SWML request
        return super().on_swml_request(request_data, callback_path, request)


def get_signalwire_host():
    """Get the full SignalWire host from space name."""
    space = os.getenv("SIGNALWIRE_SPACE_NAME", "")
    if not space:
        return None
    # If it's already a full domain, use it as-is
    if "." in space:
        return space
    # Otherwise append .signalwire.com
    return f"{space}.signalwire.com"


def find_existing_handler(sw_host, auth, agent_name):
    """Find an existing SWML handler by name."""
    try:
        # List all external SWML handlers
        resp = requests.get(
            f"https://{sw_host}/api/fabric/resources/external_swml_handlers",
            auth=auth,
            headers={"Accept": "application/json"}
        )
        if resp.status_code != 200:
            print(f"Failed to list handlers: {resp.status_code}")
            return None

        handlers = resp.json().get("data", [])

        for handler in handlers:
            # The name is nested in swml_webhook object
            swml_webhook = handler.get("swml_webhook", {})
            handler_name = swml_webhook.get("name") or handler.get("display_name")

            # Check if this handler matches our agent name
            if handler_name == agent_name:
                handler_id = handler.get("id")
                handler_url = swml_webhook.get("primary_request_url", "")
                # Get the address for this handler
                addr_resp = requests.get(
                    f"https://{sw_host}/api/fabric/resources/external_swml_handlers/{handler_id}/addresses",
                    auth=auth,
                    headers={"Accept": "application/json"}
                )
                if addr_resp.status_code == 200:
                    addresses = addr_resp.json().get("data", [])
                    if addresses:
                        return {
                            "id": handler_id,
                            "name": handler_name,
                            "url": handler_url,
                            "address_id": addresses[0]["id"],
                            "address": addresses[0]["channels"]["audio"]
                        }
    except Exception as e:
        print(f"Error checking existing handlers: {e}")
    return None


def setup_swml_handler():
    """Set up SWML handler on startup."""
    sw_host = get_signalwire_host()
    project = os.getenv("SIGNALWIRE_PROJECT_ID", "")
    token = os.getenv("SIGNALWIRE_TOKEN", "")
    agent_name = os.getenv("AGENT_NAME", "santa")
    proxy_url = os.getenv("SWML_PROXY_URL_BASE", os.getenv("APP_URL", ""))
    auth_user = os.getenv("SWML_BASIC_AUTH_USER", "")
    auth_pass = os.getenv("SWML_BASIC_AUTH_PASSWORD", "")

    if not all([sw_host, project, token]):
        print("SignalWire credentials not configured - skipping SWML handler setup")
        return

    if not proxy_url:
        print("SWML_PROXY_URL_BASE/APP_URL not set - skipping SWML handler setup")
        return

    # Build SWML URL with basic auth credentials
    if auth_user and auth_pass and "://" in proxy_url:
        scheme, rest = proxy_url.split("://", 1)
        swml_url = f"{scheme}://{auth_user}:{auth_pass}@{rest}/santa"
    else:
        swml_url = proxy_url + "/santa"

    auth = (project, token)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Look for an existing handler by name
    existing = find_existing_handler(sw_host, auth, agent_name)
    if existing:
        swml_handler_info["id"] = existing["id"]
        swml_handler_info["address_id"] = existing["address_id"]
        swml_handler_info["address"] = existing["address"]

        # Always update the URL to ensure credentials are current
        # (API may return masked URLs making comparison unreliable)
        try:
            update_resp = requests.put(
                f"https://{sw_host}/api/fabric/resources/external_swml_handlers/{existing['id']}",
                json={
                    "primary_request_url": swml_url,
                    "primary_request_method": "POST"
                },
                auth=auth,
                headers=headers
            )
            update_resp.raise_for_status()
            print(f"Updated SWML handler: {existing['name']}")
        except Exception as e:
            print(f"Failed to update handler URL: {e}")

        print(f"Call address: {existing['address']}")
    else:
        # Create a new external SWML handler with the agent name
        try:
            handler_resp = requests.post(
                f"https://{sw_host}/api/fabric/resources/external_swml_handlers",
                json={
                    "name": agent_name,
                    "used_for": "calling",
                    "primary_request_url": swml_url,
                    "primary_request_method": "POST"
                },
                auth=auth,
                headers=headers
            )
            handler_resp.raise_for_status()
            handler_id = handler_resp.json().get("id")
            swml_handler_info["id"] = handler_id

            # Get the address for this handler
            addr_resp = requests.get(
                f"https://{sw_host}/api/fabric/resources/external_swml_handlers/{handler_id}/addresses",
                auth=auth,
                headers={"Accept": "application/json"}
            )
            addr_resp.raise_for_status()
            addresses = addr_resp.json().get("data", [])
            if addresses:
                swml_handler_info["address_id"] = addresses[0]["id"]
                swml_handler_info["address"] = addresses[0]["channels"]["audio"]
                print(f"Created SWML handler: {agent_name}")
                print(f"Call address: {swml_handler_info['address']}")
            else:
                print("No address found for handler")
        except Exception as e:
            print(f"Failed to create SWML handler: {e}")
            # Retry finding existing handler (another worker may have just created it)
            import time
            time.sleep(0.5)
            existing = find_existing_handler(sw_host, auth, agent_name)
            if existing:
                swml_handler_info["id"] = existing["id"]
                swml_handler_info["address_id"] = existing["address_id"]
                swml_handler_info["address"] = existing["address"]
                print(f"Found existing SWML handler after retry: {existing['name']}")
                print(f"Call address: {existing['address']}")


def create_server():
    """Create AgentServer with static file mounting and API endpoints."""
    server = AgentServer(host=HOST, port=PORT)
    server.register(SantaAIAgent(), "/santa")

    # Serve static files using SDK's built-in method
    web_dir = Path(__file__).parent / "web"
    if web_dir.exists():
        server.serve_static_files(str(web_dir))

    # Add /get_token endpoint for WebRTC calls
    @server.app.get('/get_token')
    def get_token():
        """Get a guest token for the web client to call the agent."""
        sw_host = get_signalwire_host()
        project = os.getenv("SIGNALWIRE_PROJECT_ID", "")
        token = os.getenv("SIGNALWIRE_TOKEN", "")

        if not all([sw_host, project, token]):
            return JSONResponse({"error": "SignalWire credentials not configured"}, status_code=500)

        if not swml_handler_info["address_id"]:
            return JSONResponse({"error": "SWML handler not configured - check startup logs"}, status_code=500)

        auth = (project, token)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            # Create a guest token with access to this address
            expire_at = int(time.time()) + 3600 * 24  # 24 hours

            guest_resp = requests.post(
                f"https://{sw_host}/api/fabric/guests/tokens",
                json={
                    "allowed_addresses": [swml_handler_info["address_id"]],
                    "expire_at": expire_at
                },
                auth=auth,
                headers=headers
            )
            guest_resp.raise_for_status()
            guest_token = guest_resp.json().get("token", "")

            return {
                "token": guest_token,
                "address": swml_handler_info["address"]
            }

        except requests.exceptions.RequestException as e:
            print(f"Token request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return JSONResponse({"error": str(e)}, status_code=500)

    # Add /get_credentials endpoint for curl examples
    @server.app.get('/get_credentials')
    def get_credentials():
        """Get basic auth credentials for the web UI."""
        return {
            "user": os.getenv("SWML_BASIC_AUTH_USER", ""),
            "password": os.getenv("SWML_BASIC_AUTH_PASSWORD", "")
        }

    # Add /get_resource_info endpoint for dashboard links
    @server.app.get('/get_resource_info')
    def get_resource_info():
        """Get SWML handler resource info for linking to SignalWire dashboard."""
        sw_host = get_signalwire_host()
        return {
            "space_name": os.getenv("SIGNALWIRE_SPACE_NAME", ""),
            "resource_id": swml_handler_info["id"],
            "dashboard_url": f"https://{sw_host}/neon/resources/{swml_handler_info['id']}/edit?t=addresses" if sw_host and swml_handler_info["id"] else None
        }

    return server


# Set up SWML handler on module load
setup_swml_handler()

# Create server and expose app for gunicorn
server = create_server()
app = server.app

if __name__ == "__main__":
    server.run()
