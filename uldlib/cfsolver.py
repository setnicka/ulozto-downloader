import requests
import json

from urllib.parse import urlencode, quote_plus

from uldlib import const

class DummyResponse:
    text = ""
    status_code = 0
    cookies = {}
    user_agent = ""

class CFSolver:
    session = None
    raw_proxy = {}
    headers = requests.utils.default_headers()
    cookies = None
    user_agent = None
    flaresolverr_endpoint = const.DEFAULT_CF_ENDPOINT

    def __init__(self, endpoint: str = None, timeout: int = 120) -> None:
        if endpoint:
            self.flaresolverr_endpoint = endpoint

        self.s = requests.Session()
        self.timeout = timeout*1000

        self.options = {
            "maxTimeout": self.timeout
        }

        # Test if the Flaresolverr service is reachable
        if self.list_sessions() == False:
            raise RuntimeError(
                "Failed to connect to the Flaresolverr service. "
                "Make sure it's reachable or specify an alternative endpoint using the --cf-endpoint argument."
            )

        pass

    def __del__(self) -> None:
        self.destroy_session()
        pass

    def get_timeout(self):
        return int(self.timeout/1000)

    def set_proxy(self, proxies={}) -> None:
        """ Configures the (Tor) proxy into the Falresoverr service.
        """
        
        if (proxies and proxies.get('https')):
            self.raw_proxy = proxies
            proxy_url = proxies.get('https')

            self.options['proxy'] = {
                "url": proxy_url
            }
        else:
            raise RuntimeError(f"Failed to configure Cloudflare solver proxy {proxies}.")
       
    def get_session(self):
        """ Returns the existing Flaresolverrr session or creates a new one if no
        session exists yet.
        """

        if not self.session:
            self.session = self.create_session()
        
        return self.session

    def list_sessions(self):
        options = {}
        options['cmd'] = "sessions.list"
        
        try:
            r = self.s.post(
                self.flaresolverr_endpoint,
                data = json.dumps(options),
                headers = {
                    'Content-Type': 'application/json'
                })
            
            result = json.loads(r.text)

            if (result.get('status') and result.get('status') == "ok"):
                return result.get('sessions')
            else:
                return False
        except:
            return False
        
    def create_session(self):
        options = {}
        options['cmd'] = "sessions.create"
        if self.options.get('proxy'):
            options['proxy'] = self.options.get('proxy')

        r = self.s.post(
            self.flaresolverr_endpoint,
            data = json.dumps(options),
            headers = {
                'Content-Type': 'application/json'
            })
        
        result = json.loads(r.text)
        
        if (result.get('status') and result.get('status') == "ok"):
            return result.get('session')
    
    def destroy_session(self) -> bool:
        if not self.session:
            return False
        
        options = {}
        options['cmd'] = "sessions.destroy"
        options['session'] = self.session

        r = self.s.post(
            self.flaresolverr_endpoint,
            data = json.dumps(options),
            headers = {
                'Content-Type': 'application/json'
            })
        
        result = json.loads(r.text)

        if (result.get('status') and result.get('status') == "ok"):
            del self.session
            return True
        else:
            return False

    def request(self, target, timeout=60, cmd='request.get', req_data={}) -> None:
        options = self.options.copy()
        options['session'] = self.get_session()
        options['url'] = target
        options['cmd'] = cmd

        # Re-use the CF cookie if present to avoid solving multiple challenges
        if self.cookies and self.cookies.get("cf_clearance"):
            options['cookies'] = [{"name": "cf_clearance", "value": self.cookies.get("cf_clearance")}]

        if cmd == 'request.post':
            options['postData'] = req_data

        r = self.s.post(
            self.flaresolverr_endpoint,
            data = json.dumps(options),
            headers = {
                'Content-Type': 'application/json'
            })
            
        result = json.loads(r.text)
            
        if (result.get('solution')):
            # Store cookies and User Agent for future use
            cookies = result.get('solution').get('cookies')
            self.cookies = {cookie['name']: cookie['value'] for cookie in cookies}
            self.user_agent = result.get('solution').get('userAgent')

            # Prepare a response compatible with the Requests library
            data = DummyResponse()
            data.text = result.get('solution').get('response')
            data.status_code = result.get('solution').get('status')
            data.cookies = self.get_cookies()
            data.user_agent = self.get_user_agent()

            return data
        elif (result.get('status') == "error"):
            raise RuntimeError(f"Cloudflare solver error: {result.get('message')}")
        else:
            raise RuntimeError(f"Failed to solve Cloudflare challenge: {result}")
    
    def get(self, target, timeout=60):
        return self.request(target, timeout, 'request.get')
    
    def post(self, target, data={}, timeout=60):
        return self.request(target, timeout, 'request.post', urlencode(data, quote_via=quote_plus))
    
    def XHRpost(self, target, data={}, timeout=60):
        """Makes an XHR POST request reusing User Agent and Cookies captured from
        previous succesfull get requests to bypas the CloudFlare WAF.
        """

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip",
            "X-Requested-With": "XMLHttpRequest"
        }
        r = requests.post(target, headers=headers, cookies=self.cookies, data=data, timeout=timeout, proxies=self.raw_proxy)

        return r
    
    def get_cookies(self, all:bool=False):
        """Returns the cookies obtained from the Flaresolverr browser.
        By default only the cookies necessary to bypass the CloudFlare challenge are returned.
        :param bool all: Return all the browser cookies, defaults to False
        """
    
        if all:
            return self.cookies
        elif self.cookies and self.cookies.get("cf_clearance"):
            return {"cf_clearance": self.cookies.get("cf_clearance")}
        else:
            return {}
    
    def get_user_agent(self):
        """Returns the User Agent used by the Flaresolverr browser to obtain the CloudFlare clearance.
        """

        return self.user_agent