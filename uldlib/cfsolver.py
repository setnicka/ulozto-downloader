import requests
import json

class DummyResponse:
    text = ""
    status_code = 0

class CFSolver:
    session = None

    def __init__(self, timeout: int = 120) -> None:
        self.s = requests.Session()
        self.timeout = timeout*1000

        self.options = {
            "maxTimeout": self.timeout
        }

        pass

    def get_timeout(self):
        return int(self.timeout/1000)

    def set_proxy(self, proxies={}) -> None:
        if (proxies and proxies.get('https')):
            self.options['proxy'] = {
                "url": proxies.get('https')
            }
        else:
            raise RuntimeError(f"Failed to configure Cloudflare solver proxy {proxies}.")
       
    def get_session(self):
        if not self.session:
            self.session = self.create_session()
        
        return self.session

    def create_session(self):
        options = self.options.copy()
        options['cmd'] = "sessions.create"

        r = self.s.post(
            'http://localhost:8191/v1',
            data = json.dumps(options),
            headers = {
                'Content-Type': 'application/json'
            })
        
        result = json.loads(r.text)
        #print(result)
        if (result.get('solution')):
            return result.get('solution').get('session')

    def get(self, target) -> None:
        options = self.options.copy()
        options['session'] = self.get_session()
        options['url'] = target
        options['cmd'] = "request.get"

        r = self.s.post(
            'http://localhost:8191/v1',
            data = json.dumps(options),
            headers = {
                'Content-Type': 'application/json'
            })
        
        result = json.loads(r.text)
        
        if (result.get('solution')):
            cookies = result.get('solution').get('cookies')
            for cookie in cookies:
                del cookie['httpOnly']
                del cookie['sameSite']
                cookie['expires'] = cookie.get('expiry')
                if (cookie.get('expiry')):
                    del cookie['expiry']

                self.s.cookies.set_cookie(requests.cookies.create_cookie(**cookie))

            self.user_agent = result.get('solution').get('userAgent')

            data = DummyResponse()
            data.text = result.get('solution').get('response')
            data.status_code = result.get('solution').get('status')

            return data
        elif (result.get('status') == "error"):
            raise RuntimeError(f"Cloudflare solver error: {result.get('message')}")
        else:
            raise RuntimeError(f"Failed to solve Cloudflare challenge: {result}")
    
    def post(self, target, data={}, headers={}, timeout=60):
        #options['session'] = self.get_sesion()

        headers = {
            "Accept-Encoding": "gzip",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": self.user_agent,
        }
        
        s = self.s.post(target, data=data, timeout=timeout, headers=headers)
        
        return s
    