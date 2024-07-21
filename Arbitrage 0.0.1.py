import time
import requests
import urllib.parse
import hashlib
import hmac
import base64
import itertools
from colorama import init, Fore, Style

init()

# Find all currencies and filters for current program capabilities
# URL for Kraken API endpoint to get asset info
url_currencies = "https://api.kraken.com/0/public/Assets"

# Send a GET request to the API endpoint
response = requests.get(url_currencies)

# Check if the request was successful
if response.status_code == 200:
    # Extract the asset data from the response
    assets_data = response.json()["result"]
    # Extract all currency symbols (asset names)
    all_currencies = list(assets_data.keys())
else:
    print("Failed to retrieve data from Kraken API")

adjusted_all_currencies = {}

for currency in all_currencies:
    # Adjust currency name if it has 4 letters and starts with 'X' or 'Z'
    if len(currency) == 4 and (currency[0] == 'X' or currency[0] == 'Z'):
        adjusted_currency = currency[1:]
    else:
        adjusted_currency = currency
    
    adjusted_all_currencies[adjusted_currency] = currency

banned_currencies = {currency for currency in adjusted_all_currencies if len(currency) >= 4}
available_currencies = {currency for currency in adjusted_all_currencies if len(currency) == 3}

#Finds all available valid pairs
response_pairs = requests.get('https://api.kraken.com/0/public/AssetPairs')
data_pairs = response_pairs.json()
valid_pairs = list(data_pairs['result'].keys())

adjusted_valid_pairs = []

for valid_pair in valid_pairs:
    if len(valid_pair) == 8 and valid_pair[0] in ['X', 'Z']:
        semi_adjusted_valid_pair_name = valid_pair[1:]
        if len(semi_adjusted_valid_pair_name) == 7 and semi_adjusted_valid_pair_name[3] in ['X', 'Z']: #Does same thing for the second part
            adjusted_valid_pair_name = semi_adjusted_valid_pair_name[:3] + semi_adjusted_valid_pair_name[4:]
            adjusted_valid_pairs.append(adjusted_valid_pair_name)
        else:
            print(f"Error in part 2 of {valid_pair}")
    else:
        adjusted_valid_pairs.append(valid_pair)

# Obtain API keys
with open ("keys.txt", "r") as f:
    lines = f.read().splitlines()
    api_key = lines[0]
    api_sec = lines[1]

api_url = "https://api.kraken.com"

def get_kraken_signature(urlpath, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = str(data['nonce'] + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

def kraken_request(url_path, data, api_key, api_sec):
    headers = {"API-Key":api_key, "API-Sign":get_kraken_signature(url_path, data, api_sec)}
    balance = requests.post((api_url + url_path), headers=headers, data=data)
    return balance 

def get_tradable_currencies_with_balance(filtered_balances):
    response_pairs = requests.get('https://api.kraken.com/0/public/AssetPairs')
    data_pairs = response_pairs.json()

    tradable_currencies_with_balance = set()

    if 'result' in data_pairs:
        asset_pairs = data_pairs['result']
        for pair_name, pair_info in asset_pairs.items():
            currencies = pair_info['wsname'].split('/')
            if chosen_currency in currencies:
                for currency in currencies:
                    if currency != chosen_currency and currency not in filtered_balances:  # Exclude chosen currencies and owned currencies
                        tradable_currencies_with_balance.add(currency)

    return tradable_currencies_with_balance

#gathers current balances
balance_response = kraken_request("/0/private/Balance", {"nonce":str(int(1000 * time.time()))}, api_key, api_sec)
balance_data = balance_response.json()

if 'result' in balance_data:
    balances = balance_data['result']
    filtered_balance = {key: value for key, value in balances.items() if float(value) > 0}

    # Create a new filtered balance dictionary with adjusted currency names
    adjusted_filtered_balance = {}
    for currency, balance in filtered_balance.items():
        # Adjust currency name if it has 4 letters and starts with 'X' or 'Z'
        if len(currency) == 4:
            if currency[0] == 'X':
                adjusted_currency = currency[1:]
            elif currency[0] == 'Z':
                adjusted_currency = currency[1:]
            else:
                adjusted_currency = currency
        else:
            adjusted_currency = currency
        
        adjusted_filtered_balance[adjusted_currency] = balance

    # Display available currencies with their balances to the user
    print("Available currencies with balances:")
    for currency, balance in adjusted_filtered_balance.items():
        print(f"{currency}: {balance}")

    # Prompt the user to choose a currency
    while True:
        chosen_currency = input("Choose a currency: ")
        if chosen_currency in adjusted_filtered_balance:
            break
        else:
            print("Invalid currency name. Please choose from the available currencies.")

else:
    print("Error: No balance data found in the response.")

pairs_with_chosen_currency = []  # Initialize an empty list to hold the found pair names

if 'result' in data_pairs:
    # asset_pairs = data_pairs['result'] #Parked for now
    filtered_pairs = [pair for pair in valid_pairs if (chosen_currency in pair or chosen_currency in pair.replace("/", "")) and all(banned_currency not in pair for banned_currency in banned_currencies)]
    if filtered_pairs:
        for pair_name in filtered_pairs:
            adjusted_pair_name = pair_name
            # Adjust the pair name if it's 8 characters long and starts with 'X' or 'Z'
            if len(pair_name) == 8 and pair_name[0] in ['X', 'Z']:
                semi_adjusted_pair_name = pair_name[1:]
                if len(semi_adjusted_pair_name) == 7 and semi_adjusted_pair_name[3] in ['X', 'Z']: #Does same thing for the second part
                    adjusted_pair_name = semi_adjusted_pair_name[:3] + semi_adjusted_pair_name[4:]
            
            if adjusted_pair_name in adjusted_valid_pairs:
                pairs_with_chosen_currency.append(adjusted_pair_name) # Append the found pair name to the list
            else:
                print(f"Error: Couldn't find for {adjusted_pair_name}")
            
    else:
        print(f"No asset pairs found for {chosen_currency}.")
else:
    print("No asset pairs found in the response.")

#lists out the currencies that are paired
if 'result' in balance_data:
    balances = balance_data['result']
    filtered_balance = {key: value for key, value in balances.items() if float(value) > 0}
    owned_currencies = filtered_balance.keys()

    tradable_currencies_with_balance = get_tradable_currencies_with_balance(set(owned_currencies))

#finds bridges to finalise all possible triangles
bridges = []  # Initialize an empty list to store found pairs

if 'result' in balance_data:
    tradable_currencies_with_balance = get_tradable_currencies_with_balance(set())

    for currency1 in tradable_currencies_with_balance:
        for currency2 in tradable_currencies_with_balance:
            if currency1 != currency2 and currency1 not in banned_currencies and currency2 not in banned_currencies:  # Exclude pairs of the same currency and banned currencies
                potential_bridge = f"{currency1}{currency2}"
                
                if potential_bridge in adjusted_valid_pairs:
                    bridges.append(potential_bridge)

else:
    print("Error: No balance data found in the response.")

if 'result' in balance_data:
    # Generate all possible permutations with 3 placeholders
    placeholders = [pairs_with_chosen_currency, bridges, pairs_with_chosen_currency]
    all_permutations = list(itertools.product(*placeholders))

    # Filter out permutations where the first and third placeholders are the same
    filtered_permutations = [p for p in all_permutations if (p[0] != p[2] and all(len(placeholder) ==6 for placeholder in p))]
    # Define a function to get residues from placeholders
    def get_residue(placeholder, chosen_currency):
        residue = placeholder.replace(chosen_currency, "")
        if len(residue) == 4 and residue[0] in ['Z', 'X']:
            residue = residue[1:]
        return residue
    
    # Filter permutations based on residue conditions and print intermediate results
    new_filtered_permutations = []
    for p in filtered_permutations:
        residue1 = get_residue(p[0], chosen_currency)
        residue2 = get_residue(p[2], chosen_currency)
        residue_concatenation = residue1 + residue2
        residue_concatenation_reverse = residue2 + residue1
        if p[1] in [residue_concatenation, residue_concatenation_reverse]:
            new_filtered_permutations.append(p)
    
    # Modify the first placeholder based on chosen currency position
    for idx, permutation in enumerate(new_filtered_permutations):
        residue_1 = get_residue(permutation[0], chosen_currency)
        if chosen_currency in permutation[0][:3]:
            if chosen_currency in permutation[2][:3]:
                
                if residue_1 in permutation[0][-3:] and residue_1 in permutation[1][:3]:
                    new_filtered_permutations[idx] = (permutation[0], 'sell', permutation[1], 'sell', permutation[2], 'buy')
                elif residue_1 in permutation[0][-3:] and residue_1 in permutation[1][-3:]:
                    new_filtered_permutations[idx] = (permutation[0], 'sell', permutation[1], 'buy', permutation[2], 'buy')
            
            if chosen_currency in permutation[2][3:]:
                if residue_1 in permutation[0][-3:] and residue_1 in permutation[1][:3]:
                    new_filtered_permutations[idx] = (permutation[0], 'sell', permutation[1], 'sell', permutation[2], 'sell')
                elif residue_1 in permutation[0][-3:] and residue_1 in permutation[1][-3:]:
                    new_filtered_permutations[idx] = (permutation[0], 'sell', permutation[1], 'buy', permutation[2], 'sell')
    
        elif chosen_currency in permutation[0][3:]:
            if chosen_currency in permutation[2][:3]:
                
                if residue_1 in permutation[0][:3] and residue_1 in permutation[1][:3]:
                    new_filtered_permutations[idx] = (permutation[0], 'buy', permutation[1], 'sell', permutation[2], 'buy')
                elif residue_1 in permutation[0][:3] and residue_1 in permutation[1][-3:]:
                    new_filtered_permutations[idx] = (permutation[0], 'buy', permutation[1], 'buy', permutation[2], 'buy')
            
            if chosen_currency in permutation[2][3:]:
                if residue_1 in permutation[0][:3] and residue_1 in permutation[1][:3]:
                    new_filtered_permutations[idx] = (permutation[0], 'buy', permutation[1], 'sell', permutation[2], 'sell')
                elif residue_1 in permutation[0][:3] and residue_1 in permutation[1][-3:]:
                    new_filtered_permutations[idx] = (permutation[0], 'buy', permutation[1], 'buy', permutation[2], 'sell')
    
    print("\nPossible Triangular Arbritrage Systems:")
    for new_filtered_permutation in new_filtered_permutations:
        print(new_filtered_permutation)

else:
    print("Error: No balance data found in the response.")

# Final part for analysis
math_new_filtered_permutations = new_filtered_permutations

# Function to fetch spot price from Kraken API
def fetch_spot_price(pair):
    try:
        response = requests.get(f"https://api.kraken.com/0/public/Ticker?pair={pair}")
        data = response.json()
        if 'result' in data:
            first_key = next(iter(data['result']))  # Get the first key in 'result'
            if 'c' in data['result'][first_key]:
                return float(data['result'][first_key]['c'][0])
            else:
                print(f"Failed to fetch spot price for pair: {pair}. 'c' not found in the response.")
                return None
        else:
            print(f"Failed to fetch spot price for pair: {pair}. 'result' not found in the response.")
            return None
    except Exception as e:
        print(f"Error fetching spot price for pair {pair}: {e}")
        return None


# Function to adjust spot price based on action
def adjust_spot_price(spot_price, action):
    if action == 'buy': #DO NOT CHANGE FROM BUY OTHERWISE YOU'LL GO THE WRONG WAY
        return 1 / spot_price
    else:
        return spot_price

# Function to calculate product of spot prices for each permutation group
def calculate_product(permutations):
    product = 1
    for pair, action in permutations:
        spot_price = fetch_spot_price(pair)
        if spot_price is not None:
            spot_price = adjust_spot_price(spot_price, action)
            product *= spot_price
        else:
            return None  # If spot price is not available, return None
    return product

# Main loop
while True:
    print("\n")
    for idx, permutation in enumerate(math_new_filtered_permutations):
        # Extract pairs and actions from permutation
        pairs_actions = [(permutation[i], permutation[i + 1]) for i in range(0, len(permutation), 2)]
        
        # Calculate product of spot prices for each permutation group
        product = calculate_product(pairs_actions)
                
        # Print product if available
        if product is not None:
            if product > 1:
                print(Fore.GREEN + f"Arbitrage for {permutation[0]}, {permutation [2]}, {permutation[4]}: {product}")
            else:
                print(Fore.RED + f"Arbitrage for {permutation[0]}, {permutation [2]}, {permutation[4]}: {product}" + Style.RESET_ALL)
        else:
            print(f"Arbitrage for {permutation[0]}, {permutation [2]}, {permutation[4]}: N/A (Some spot prices not available)")

    time.sleep(1)