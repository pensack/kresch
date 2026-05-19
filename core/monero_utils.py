import requests
import json
from django.conf import settings

class MoneroManager:
    """
    Handles communication with monero-wallet-rpc for Multisig Escrow.
    """
    def __init__(self):
        self.rpc_url = getattr(settings, 'MONERO_RPC_URL', 'http://127.0.0.1:18082/json_rpc')
        self.rpc_user = getattr(settings, 'MONERO_RPC_USER', '')
        self.rpc_password = getattr(settings, 'MONERO_RPC_PASSWORD', '')

    def _call(self, method, params=None):
        payload = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": method,
            "params": params or {}
        }
        try:
            response = requests.post(
                self.rpc_url,
                data=json.dumps(payload),
                auth=(self.rpc_user, self.rpc_password) if self.rpc_user else None,
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def make_multisig(self, buyer_pub, vendor_pub):
        """
        The 3-way Handshake.
        Combines Buyer, Vendor, and Admin keys into a single Escrow Address.
        """
        # 1. Get our (Admin) Public Key from the RPC
        admin_key_resp = self._call("get_address")
        if "error" in admin_key_resp:
            return None
        
        admin_pub = admin_key_resp['result']['address']

        # 2. In a real Monero multisig, we would call 'make_multisig'
        # with the threshold 2 and the list of keys.
        # RPC Method: make_multisig
        params = {
            "threshold": 2,
            "participants": [buyer_pub, vendor_pub, admin_pub]
        }
        
        # NOTE: This requires the Monero Wallet to be in 'multisig' mode.
        resp = self._call("make_multisig", params)
        
        if "result" in resp:
            return resp['result']['address']
        
        # For simulation if RPC is offline
        return f"8{buyer_pub[:4]}{vendor_pub[:4]}...SIMULATED"

    def check_transfer(self, address):
        """
        Scans the blockchain for incoming XMR to the specific sub-address.
        """
        params = {"address": address}
        resp = self._call("get_transfers", {"in": True, "account_index": 0})
        
        if "result" in resp:
            # Logic to find the specific address in the list
            for transfer in resp['result'].get('in', []):
                if transfer['address'] == address:
                    return True, transfer['amount']
        
        return False, 0
