import os
import string
import secrets
import requests
import json
from io import BytesIO
import tarfile
from zipfile import ZipFile
from typing import Optional, Tuple
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from base64 import urlsafe_b64encode, urlsafe_b64decode
from flask import request
from googletrans import Translator # Version: 3.1.0a0
from bs4 import BeautifulSoup
import ipaddress

CURRENT_DIR = os.getcwd()
DATA_DIR = os.path.join(CURRENT_DIR, "data")

# Paths for the individual IP blocks
FIREHOL_PATH = os.path.join(DATA_DIR, "fireholipset.json")
IPDENY_PATH = os.path.join(DATA_DIR, "ipdenyipset.json")
EMERGINGTHREATS_PATH = os.path.join(DATA_DIR, "emergingthreatsipset.json")
MYIPMS_PATH = os.path.join(DATA_DIR, "myipmsipset.json")
TOREXITNODES_PATH = os.path.join(DATA_DIR, "torexitnodes.json")

# Paths for cache files, and IP log files
SEENIPS_PATH = os.path.join(DATA_DIR, "seenips.json")
CAPTCHASOLVED_PATH = os.path.join(DATA_DIR, "captchasolved.json")
STOPFORUMSPAM_PATH = os.path.join(DATA_DIR, "stopforumspamcache.json")

# Path to the captcha secret
CAPTCHASECRET_PATH = os.path.join(DATA_DIR, "captchasecret.txt")

def generate_random_string(length):
    characters = string.ascii_letters + string.digits + string.punctuation
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string

# The captcha secret is used to check the captcha of the user
if not os.path.isfile(CAPTCHASECRET_PATH):
    CAPTCHASECRET = generate_random_string(1024)
    with open(CAPTCHASECRET_PATH, "w") as file:
        file.write(CAPTCHASECRET)
else:
    with open(CAPTCHASECRET_PATH, "r") as file:
        CAPTCHASECRET = file.read()

# Check if the "fireholipset.json" file is not present
if not os.path.isfile(FIREHOL_PATH):
    # List of URLs to the FireHOL IP lists
    firehol_urls = [
        "https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_level1.netset",
        "https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_level2.netset",
        "https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_level3.netset",
        "https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_level4.netset"
    ]

    # Empty list for the collected IP addresses
    firehol_ips = []

    # Loop to retrieve and process the IP lists.
    for firehol_url in firehol_urls:
        response = requests.get(firehol_url)
        if response.ok:
            # Extract the IP addresses from the response and add them to the list
            ips = [line.strip().split('/')[0] for line in response.text.splitlines() if line.strip() and not line.startswith("#")]
            firehol_ips.extend(ips)
        else:
            response.raise_for_status()

    # Remove duplicates from the list of collected IP addresses
    FIREHOL_IPS = list(set(firehol_ips))
    
    # Open the JSON file in write mode and save the collected IP addresses
    with open(FIREHOL_PATH, "w") as file:
        json.dump(FIREHOL_IPS, file)
else:
    with open(FIREHOL_PATH, "r") as file:
        FIREHOL_IPS = json.load(file)

# Check if the "ipdenyipset.json" file is not present
if not os.path.isfile(IPDENY_PATH):
    # List of URLs to the IP deny IP lists (for IPv4 and IPv6).
    ipdeny_urls = [
        "https://www.ipdeny.com/ipblocks/data/countries/all-zones.tar.gz",
        "https://www.ipdeny.com/ipv6/ipaddresses/blocks/ipv6-all-zones.tar.gz"
    ]

    # Empty list for the collected IP addresses
    ipdeny_ips = []

    # Loop to retrieve and process the IP lists.
    for ipdeny_url in ipdeny_urls:
        response = requests.get(ipdeny_url)
        if response.ok:
            # Load the TAR-GZ file and extract its contents
            tar_file = BytesIO(response.content)
            with tarfile.open(fileobj=tar_file, mode="r:gz") as tar:
                members = tar.getmembers()
                for member in members:
                    # Check if the member is a file and has the extension ".zone".
                    if member.isfile() and member.name.endswith('.zone'):
                        # Read the contents of the file, decode it as UTF-8 and extract the IP addresses
                        file_content = tar.extractfile(member).read().decode("utf-8")
                        ips = [line.strip().split('/')[0] for line in file_content.splitlines() if line.strip() and not line.startswith("#")]
                        ipdeny_ips.extend(ips)
        else:
            response.raise_for_status()
    
    # Remove duplicates from the list of collected IP addresses
    IPDENY_IPS = list(set(ipdeny_ips))
    
    # Open the JSON file in write mode and save the collected IP addresses
    with open(IPDENY_PATH, "w") as file:
        json.dump(IPDENY_IPS, file)
else:
    with open(IPDENY_PATH, "r") as file:
        IPDENY_IPS = json.load(file)

# Check if the "emergingthreatsipset.json" file is not present
if not os.path.isfile(EMERGINGTHREATS_PATH):
    # URL to get the list of IP's
    emergingthreats_url = "https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt"
    
    # Request the list of IP's
    response = requests.get(emergingthreats_url)
    
    # Check if the request was successful
    if response.ok:
        # Extract the IP addresses from the response and remove duplicates
        emergingthreats_ips = [line.strip().split('/')[0] for line in response.text.splitlines() if line.strip() and not line.startswith("#")]
        EMERGINGTHREATS_IPS = list(set(emergingthreats_ips))
        
        # Open the JSON file in write mode and save the list of Ips.
        with open(EMERGINGTHREATS_PATH, "w") as file:
            json.dump(EMERGINGTHREATS_IPS, file)
    else:
        response.raise_for_status()
else:
    with open(EMERGINGTHREATS_PATH, "r") as file:
        EMERGINGTHREATS_IPS = json.load(file)

# Check if the "myipmsipset.json" file is not present
if not os.path.isfile(MYIPMS_PATH):
    # URL to get the list of IP's
    myipms_url = "https://myip.ms/files/blacklist/general/full_blacklist_database.zip"
    
    # Request the zip file
    response = requests.get(myipms_url)
    
    # Check if the request was successful
    if response.ok:
        with BytesIO(response.content) as zip_file:
            # Load the ZIP file and extract its contents
            with ZipFile(zip_file, "r") as z:
                with z.open("full_blacklist_database.txt", "r") as txt_file:
                    content = txt_file.read().decode('utf-8')
                    myipms_ips = [line.strip().split('/')[0].split('#')[0].replace('\t', '') for line in content.splitlines() if line.strip() and not line.startswith("#")]
                    MYIPMS_IPS = list(set(myipms_ips))
        
        # Open the JSON file in write mode and save the list of Ips.
        with open(MYIPMS_PATH, "w") as file:
            json.dump(MYIPMS_IPS, file)
    else:
        response.raise_for_status()
else:
    with open(MYIPMS_PATH, "r") as file:
        MYIPMS_IPS = json.load(file)

# Check if the "torexitnodes.json" file is not present
if not os.path.isfile(TOREXITNODES_PATH):
    # URL to get the list of Tor exit nodes
    torbulkexitlist_url = "https://check.torproject.org/torbulkexitlist"
    
    # Request the list of Tor exit nodes
    response = requests.get(torbulkexitlist_url)
    
    # Check if the request was successful
    if response.ok:
        # Extract the IP addresses from the response and remove duplicates
        torexitnodes_ip = [line.strip() for line in response.text.splitlines() if line.strip() and not line.startswith("#")]
        TOREXITNODES_IPS = list(set(torexitnodes_ip))
        
        # Open the JSON file in write mode and save the list of Tor exit nodes.
        with open(TOREXITNODES_PATH, "w") as file:
            json.dump(TOREXITNODES_IPS, file)
    else:
        response.raise_for_status()
else:
    with open(TOREXITNODES_PATH, "r") as file:
        TOREXITNODES_IPS = json.load(file)

class SymmetricCrypto:
    """
    Implementation of secure symmetric encryption with AES
    """

    def __init__(self, password: Optional[str] = None, salt_length: int = 32):
        """
        Initialize the SymmetricCrypto object with password and salt_length

        :param password: A secure encryption password, should be at least 32 characters long
        :param salt_length: The length of the salt, should be at least 16
        """

        # If the password is not given, a secure random password is created
        if password is None:
            password = secrets.token_urlsafe(64)

        self.password = password.encode()
        self.salt_length = salt_length

    def generate_key_and_salt(self) -> Tuple[bytes, bytes]:
        """
        Generates Key with KDF and a secure random Salt

        :return: The encryption key generated with PBKDF2HMAC and the randomly generated salt used to generate the key has a length of self.salt_length as Tuple
        """

        # Generate a random salt
        salt = secrets.token_bytes(self.salt_length)

        # Use PBKDF2HMAC to derive the encryption key
        kdf_ = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf_.derive(self.password)
        
        return key, salt

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypts a text with the password and a salt

        :param plaintext: The text to be encrypted, as a string
        
        :return: The text encrypted with the password and a randomly generated salt and iv
        """

        # Generate a random salt and encryption key
        key, salt = self.generate_key_and_salt()

        # Generate a random IV (Initialization Vector)
        iv = secrets.token_bytes(16)

        # Use AES in CBC mode to encrypt the plaintext
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(plaintext.encode()) + padder.finalize()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Combine salt, iv, and ciphertext, and return as a URL-safe Base64 encoded string
        return urlsafe_b64encode(salt + iv + ciphertext).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypts a text with the password and a salt

        :param ciphertext: The encrypted text, must have been encrypted with the password, as a string
        
        :return: The actual text
        """

        # Decode the URL-safe Base64 encoded ciphertext
        ciphertext = urlsafe_b64decode(ciphertext.encode())

        # Extract salt, iv, and ciphertext from the combined data
        salt, iv, ciphertext = ciphertext[:self.salt_length], ciphertext[self.salt_length:self.salt_length + 16], ciphertext[self.salt_length + 16:]

        # Derive the encryption key using the password and salt
        kdf_ = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf_.derive(self.password)

        # Decrypt the ciphertext
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
        plaintext = unpadder.update(decrypted_data) + unpadder.finalize()

        # Return the decrypted plaintext
        return plaintext.decode()

class Hashing:
    """
    Implementation of secure hashing with SHA256 and 200000 iterations
    """

    def __init__(self, salt: Optional[str] = None):
        """
        Initialize the Hashing object with salt

        :param salt: The salt, makes the hashing process more secure (Optional)
        """

        self.salt = salt

    def hash(self, plaintext: str, hash_length: int = 32) -> str:
        """
        Function to hash a plaintext

        :param plaintext: The text to be hashed
        :param hash_length: The length of the returned hashed value

        :return: The hashed plaintext
        """

        # Convert plaintext to bytes
        plaintext = str(plaintext).encode('utf-8')

        # Set the salt, which is generated randomly if it is not defined and otherwise made into bytes if it is string
        salt = self.salt
        if salt is None:
            salt = secrets.token_bytes(32)
        else:
            if not isinstance(salt, bytes):
                try:
                    salt = bytes.fromhex(salt)
                except:
                    salt = salt.encode('utf-8')

        # Create a PBKDF2 instance using the SHA-256 hash algorithm
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=hash_length,
            salt=salt,
            iterations=200000,
            backend=default_backend()
        )

        # Calculate the bytes hash
        hashed_data = kdf.derive(plaintext)

        # Make/Return the bytes hash with base64 and add the salt after it
        hash = urlsafe_b64encode(hashed_data).decode('utf-8') + "//" + salt.hex()
        return hash

    def compare(self, plaintext: str, hash: str) -> bool:
        """
        Compares a plaintext with a hashed value

        :param plaintext: The text that was hashed
        :param hash: The hashed value

        :return: The result of the comparison as bool

        :raises ValueError: If salt is None and there is no salt in the provided hash
        """

        # The salt is defined
        salt = self.salt
        if "//" in hash:
            hash, salt = hash.split("//")

        if salt is None:
            raise ValueError("Salt cannot be None if there is no salt in hash")

        # Get the hash length by making the hash from a base64 encoded string into a bytes object and measuring the length from it
        hash_length = len(urlsafe_b64decode(hash.encode('utf-8')))

        # A second hash of the plaintext is generated 
        comparisonhash = Hashing(salt=bytes.fromhex(salt)).hash(plaintext, hash_length = hash_length).split("//")[0]

        # The two hashes are compared and the result is returned
        return comparisonhash == hash

# Loading the languages lists to use them in the Languages class
with open(os.path.join(DATA_DIR, "languages.json"), "r") as file:
    LANGUAGES = json.load(file)

LANGUAGE_LIST = [language["code"] for language in LANGUAGES]

class Language:
    """
    Implementation of various methods that have something to do with languages
    """

    @staticmethod
    def speak(default: str = "en") -> str:
        """
        Function to get the language of a user

        :param default: The language to be returned if no language can be found

        :return: The language preferred by the user
        """
        
        # Get the preferred language of the user
        preferred_language = request.accept_languages.best_match(LANGUAGE_LIST)

        # If the preferred language is not None
        if preferred_language != None:
            return preferred_language
        
        # Return the default language if no user languages are provided
        return default

    @staticmethod
    def translate(text_to_translate: str, from_lang: str, to_lang: str) -> str:
        """
        Function to translate a text 'text_to_translate' from a language 'from_lang' to a language 'to_lang'

        :param text_to_translate: The text in language 'from_lang' to be translated into language 'to_lang'
        :param from_lang: The language of the 'text_to_translate', can also be 'auto'
        :param to_lang: The language in which the text should be translated 'text_to_translate'

        :return: The translated text

        :raises Exception: If no translation could be made
        """

        # If both languages match, the text is simply returned
        if from_lang == to_lang:
            return text_to_translate

        # Specify the file path to the translation file
        translations_file = os.path.join(DATA_DIR, "translations.json")
        
        if os.path.isfile(translations_file):
            # If the file exists, load the translations from the file
            with open(translations_file, "r") as file:
                translations = json.load(file)
        else:
            # If the file does not exist, initialize the translations as an empty list
            translations = []
        
        # Check if the translation is already available in the cache
        for translation in translations:
            if translation["text_to_translate"] == text_to_translate and translation["from_lang"] == from_lang and translation["to_lang"] == to_lang:
                return translation["output"]
        
        # Perform the translation using the Translator class
        translator = Translator()
        try:
            output = translator.translate(text_to_translate, src=from_lang, dest=to_lang).text
        except:
            raise Exception("The text could not be translated")
            
        try:
            output = output.encode('latin-1').decode('unicode_escape')
        except:
            pass
        
        # Cache the translation in the translations file
        translation = {
            "text_to_translate": text_to_translate, 
            "from_lang": from_lang,
            "to_lang": to_lang, 
            "output": output
        }
        translations.append(translation)
        
        with open(translations_file, "w") as file:
            json.dump(translations, file)

        # In some languages, it looks better if the first character is large
        if to_lang in ["de", "en", "es", "fr", "pt", "it"]:
            output = output[0].upper() + output[1:]
            
        return output

    @staticmethod
    def translate_page(html: str, from_lang: str, to_lang: str) -> str:
        """
        Function to translate a page into the correct language

        :param html: The untranslated page in 'from_lang'
        :param from_lang: The language of the HTML page given with 'html'
        :param to_lang: The language into which the HTML web page should be translated

        :return: The translated HTML page

        > Note: function can give a bs4 error if the html page is poorly implemented as well as errors in the individual for loops e.g. for missing attributes.
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Translate headers
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for header in headers:
            if 'ntr' not in header.attrs and not header.text == None:
                header.string = Language.translate(header.text, from_lang, to_lang)
        
        # Translate links
        links = soup.find_all('a')
        for link in links:
            if 'ntr' not in link.attrs and not link.text == None:
                link.string = Language.translate(link.text, from_lang, to_lang)
        
        # Translate paragraphs
        paragraphs = soup.find_all('p')
        for paragraph in paragraphs:
            # Ignore tags that have the 'ntr' attribute or do not contain text nodes
            if 'ntr' in paragraph.attrs or paragraph.text == None:
                continue

            # Ignores all p tags that have either an image or a link in them and not the attr linkintext
            if (len(paragraph.find_all('img')) > 0 or len(paragraph.find_all('a')) > 0) and not 'linkintext' in paragraph.attrs:
                continue
            else:
                # Translates the paragraph
                paragraph.string = Language.translate(paragraph.text, from_lang, to_lang)
        
        # Translate buttons
        buttons = soup.find_all('button')
        for button in buttons:
            if 'ntr' not in button.attrs and not button.text == None:
                button.string = Language.translate(button.text, from_lang, to_lang)
        
        # Translate input placeholders
        inputs = soup.find_all('input')
        for input_tag in inputs:
            if input_tag.has_attr('placeholder') and 'ntr' not in input_tag.attrs:
                input_tag['placeholder'] = Language.translate(input_tag['placeholder'], from_lang, to_lang)
        
        # Get the translated HTML
        translated_html = str(soup)
        return translated_html

def shorten_ipv6(ip_address: str) -> str:
    """
    Function to shorten an IPv6 IP address.

    :param ip_address: Any IP address, can also be IPv4.
    
    :return: The shortened IPv6 IP address or the given ip_address if it's not a valid IPv6.
    """
    try:
        return str(ipaddress.IPv6Address(ip_address).compressed)
    except: # ipaddress.AddressValueError
        return ip_address

def get_client_ip() -> str:
    """
    Function to get the IP address of a user.

    :return: The IP with which the client has requested the server.
    
    :raises Exception: If no IP address was found.
    """
    headers_to_check = [
        'X-Forwarded-For',
        'X-Real-Ip',
        'CF-Connecting-IP',
        'True-Client-Ip',
    ]

    for header in headers_to_check:
        if header in request.headers:
            # Extract the client's IP from the header and handle multiple IPs (e.g., proxy or VPN).
            client_ip = request.headers[header]
            client_ip = client_ip.split(',')[0].strip()
            client_ip = shorten_ipv6(client_ip) # Shortens Ipv6 to compare it better with block lists
            return client_ip

    # If no headers contain the IP, fallback to using request.remote_addr
    client_ip = request.remote_addr
    client_ip = shorten_ipv6(client_ip)  # Shortens Ipv6 to compare it better with block lists

    if client_ip is None:
        raise Exception("Failed to get the user's IP address.")

    return client_ip

class DDoSify:
    """
    Shows the user/bot a captcha before the request first if the request comes from a dangerous IP
    """

    def __init__ (
        self, app, actions: dict = {}, template_dir: Optional[str] = None, hardness: int = 2,
        botfightmode: bool = False, verificationage: int = 3600, withoutcookies: bool = False, 
        block_crawler: bool = False
    ):

        """
        Initialize the DDoSify object

        :param app: Your Flask App
        :param actions: Define what happens on certain routes/endpoint in the following format: {"/my_special_route": "let"}, where the first is the route and the action follows. The following actions are available: 'block' (blocks all requests that look suspicious, without captcha), 'let' (lets all requests through without action), 'hard' (sets the hardness for this route to 3), 'normal' (sets the hardness for this route to 2), 'easy' (sets the hardness for this route to 1). The action for each page can also be set as a tuple like here {"/my_special_route": ("/path/to/my/custom/template": 'action')}, where you can set a different captcha/block template for each page.
        :param template_dir: Where the program should use templates, the file should have "captcha.html" and "block.html" for the respective actions.
        :param hardness: The hardness of the captcha, value 1-3, where 3 is high (default = 2)
        :param botfightmode: If true a captcha is displayed to all connections, True or False (default = False)
        :param verificationage: How long the captcha verification is valid, in seconds (default = 3600 [1 hour])
        :param withoutcookies: If True, no cookie is created after the captcha is fulfilled, but only an Arg is appended to the URL
        :param block_crawler: If True, known crawlers based on their user agent will also need to solve a captcha

        :raises ValueError: If the flask app is None
        """
        
        if app is None:
            raise ValueError("The Flask app cannot be None")

        if not isinstance(actions, dict):
            actions = {}

        if not hardness in [1,2,3]:
            hardness = 2

        if not isinstance(botfightmode, bool):
            botfightmode = False

        if not isinstance(verificationage, int):
            verificationage = 3600

        if not isinstance(withoutcookies, bool):
            withoutcookies = False

        if not isinstance(block_crawler, bool):
            block_crawler = False

        self.app = app
        self.actions = actions
        self.template_dir = template_dir
        self.hardness = hardness
        self.botfightmode = botfightmode
        self.verificationage = verificationage
        self.withoutcookies = withoutcookies
        self.block_crawler = block_crawler

        app.before_request(self.show_ddosify)
        # app.after_request(self.add_args) FIXME: Function so that all links on a HTML response page get the captcha args

    def show_ddosify(self):
        """
        This function displays different DDoSify pages e.g. Captcha and Block if needed
        """

        # Get the URL path of the current request
        urlpath = urlparse(request.url).path

        # Set a default action based on the hardness level of the application
        action = "hard" if self.hardness == 3 else "normal" if self.hardness == 2 else "easy"

        # Initialize the template variable to None
        template = None

        # Iterate through the defined actions to find a matching action for the current request
        for _urlpath, _action in self.actions.items():
            # Check if the current URL path matches the defined action's URL path, the endpoint or action's URL path is set to "all"
            if _urlpath == urlpath or _urlpath == request.endpoint or _urlpath == "all":
                # If the action is defined as a tuple (template, action), extract the template and action
                if isinstance(_action, tuple):
                    _template, _action = _action
                    # Check if the specified template file or directory exists
                    if os.path.isfile(_template) or os.path.isdir(_template):
                        # If the template exists, set the template variable to its value
                        template = _template

                # Check if the action is a valid one among ["block", "let", "hard", "normal", "easy"]
                if _action in ["block", "let", "hard", "normal", "easy"]:
                    # Set the action variable to the defined action for the current request
                    action = _action

        # If the action is 'let' nothing more is executed
        if action == "let":
            return

        # When an error occurs a captcha is displayed
        error = False

        try:
            # Get the client's IP address
            clientip = WebTools.get_client_ip()
        except:
            # If an error occurs while fetching the client's IP, set the error flag
            error = True
            clientip = None

        try:
            # Get the client's user agent string from the request
            clientuseragent = request.user_agent.string
        except:
            # If an error occurs while fetching the user agent, set the error flag
            error = True
            clientuseragent = None
        else:
            # If the user agent is None, set the error flag
            if clientuseragent == None:
                error = True

        # Check if the client's user agent indicates that it is a web crawler
        is_crawler = False
        if not error:
            for crawlername in crawler_user_agents:
                if crawlername.lower() in clientuseragent.lower():
                    is_crawler = True

        # Define the criteria for blocking or showing captcha
        criteria = [
            error,
            clientip in FIREHOL_IPS,
            clientip in IPDENY_IPS,
            clientip in EMERGINGTHREATS_IPS,
            clientip in MYIPMS_IPS,
            clientip in TOREXITNODES_IPS,
            self.botfightmode,
            is_crawler and self.block_crawler,
        ]

        # If none of the criteria is True and the action is not "let" proceed to check StopForumSpam API
        if not any(criteria):
            # Check if the StopForumSpam cache file exists and load its content
            if os.path.isfile(STOPFORUMSPAM_PATH):
                with open(STOPFORUMSPAM_PATH, "r") as file:
                    stopforumspamcache = json.load(file)
            else:
                # If the cache file doesn't exist, create an empty dictionary
                stopforumspamcache = {}

            # Variable indicating whether the IP was found in the cache
            found = False
            
            # Check if the client's IP exists in the StopForumSpam cache
            for hashed_ip, content in stopforumspamcache.items():
                comparison = Hashing().compare(clientip, hashed_ip)
                if comparison:
                    # The IP was found in the cache
                    found = True
                    
                    # If the IP is flagged as a spammer and the time since last check is less than 7 days (604800 seconds), block the request
                    if content["spammer"] and not int(time()) - int(content["time"]) > 604800:
                        criteria.append(True)
                    break

            if not found:
                # If the IP is not found in the cache, make a request to the StopForumSpam API
                response = requests.get(f"https://api.stopforumspam.org/api?ip={clientip}&json")
                if response.ok:
                    try:
                        content = response.json()
                    except:
                        # If an error occurs while parsing the API response, block the request
                        criteria.append(True)
                    else:
                        spammer = False
                        # Check if the IP appears in the StopForumSpam database and set the spammer flag accordingly
                        if content["ip"]["appears"] > 0:
                            spammer = True
                            criteria.append(True)

                        # The clientip is hashed and stored like this
                        hashed_clientip = Hashing().hash(clientip)

                        # Update the StopForumSpam cache with the result and current timestamp
                        stopforumspamcache[hashed_clientip] = {"spammer": spammer, "time": int(time())}
                        with open(STOPFORUMSPAM_PATH, "w") as file:
                            json.dump(stopforumspamcache, file)
                else:
                    # If the request to the API fails, block the request
                    criteria.append(True) 