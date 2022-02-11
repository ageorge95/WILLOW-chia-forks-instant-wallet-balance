import sys
from sys import path
from os import path as os_path
clvm_rs_root = os_path.join(sys._MEIPASS, 'clvm_rs_0_1_2/clvm_rs') if '_MEIPASS' in sys.__dict__\
                                           else os_path.abspath(os_path.join(os_path.dirname(__file__), 'clvm_rs_0_1_2/clvm_rs'))
path.insert(0, clvm_rs_root)

from json import load,\
    dump
from tabulate import tabulate
from traceback import format_exc
import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)
sys.path.insert(0,os_path.join(os_path.dirname(__file__)))
sys.path.insert(0,os_path.join(os_path.dirname(__file__), 'chia_blockchain'))
from chia_blockchain.chia.util.keychain import mnemonic_to_seed
from chia_blockchain.chia.util.bech32m import encode_puzzle_hash,\
    decode_puzzle_hash
from chia_blockchain.chia.consensus.coinbase import create_puzzlehash_for_pk
from chia_blockchain.chia.util.ints import uint32
from blspy import AugSchemeMPL
from chia_blockchain.chia.wallet.derive_keys import master_sk_to_wallet_sk
from _00_config import initial_config
from _00_base import db_wrapper_selector
from chia_blockchain.chia.util.byte_types import hexstr_to_bytes
from io import StringIO
from clvm_tools.cmds import brun

class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout

def get_brun_output(asset_ID,
                    ph):

    with Capturing() as output:
        brun(["", "(a (q 2 30 (c 2 (c 5 (c 23 (c (sha256 28 11) (c (sha256 28 5) ()))))))"
                             " (c (q (a 4 . 1) (q . 2) (a (i 5 (q 2 22 (c 2 (c 13 (c (sha256 26 (sha256 28 20)"
                             " (sha256 26 (sha256 26 (sha256 28 18) 9) (sha256 26 11 (sha256 28 ())))) ())))) (q . 11)) 1)"
                             " 11 26 (sha256 28 8) (sha256 26 (sha256 26 (sha256 28 18) 5)"
                             " (sha256 26 (a 22 (c 2 (c 7 (c (sha256 28 28) ())))) (sha256 28 ())))) 1))",
                             "(0x72dec062874cd4d3aab892a0906688a1ae412b0109982e1797a170add88bdcdc"
                             " 0x{asset_ID}"
                             " 0x{ph})".format(asset_ID=asset_ID,
                                               ph=ph)])
    return output[0]

class WILLOW_back_end():

    def __init__(self):

        config_path = 'config_willow.json' if '_MEIPASS' in sys.__dict__\
                                           else os_path.join(os_path.dirname(__file__),'config_willow.json')
        self.print_payload = []

        if os_path.isfile(config_path):
            try:
                with open(config_path, 'r') as json_in_handle:
                    self.config = load(json_in_handle)
            except:
                self.config = initial_config
        else:
            self.config = initial_config
            with open(config_path, 'w') as json_out_handle:
                dump(self.config, json_out_handle, indent=2)

        super(WILLOW_back_end, self).__init__()

    def _encode_puzzle_hash(self,
                            puzzle_hash,
                            prefix):
        if type(puzzle_hash) == str:
            puzzle_hash = hexstr_to_bytes(puzzle_hash)
        return encode_puzzle_hash(puzzle_hash=puzzle_hash,
                                  prefix=prefix)

    def _decode_puzzle_hash(self,
                            address: str):
        return decode_puzzle_hash(address=address)

    def return_addresses(self,
                         mnemonic: str,
                         prefix: str,
                         nr_of_addresses: int = 500) -> list:

        if self.check_mnemonic_integrity(mnemonic):

            self.print_payload.append(['info',
                                       'Generating {} addresses based on the provided mnemonic. Please wait ...'.format(nr_of_addresses)])
            all_addresses = []
            try:
                seed = mnemonic_to_seed(mnemonic=mnemonic,
                                        passphrase='')
                sk = AugSchemeMPL.key_gen(seed)

                for i in range(nr_of_addresses):
                    all_addresses.append(encode_puzzle_hash(create_puzzlehash_for_pk(master_sk_to_wallet_sk(sk, uint32(i)).get_g1()), prefix))
                self.print_payload.append(['info',
                                           '{} addresses successfully generated:\n{}'.format(nr_of_addresses,'\n'.join(all_addresses))])
            except:
                self.print_payload.append(['error',
                                           'Oh snap ! There was an error while generating the addresses:\n{}'.format(format_exc(chain=False))])

            return all_addresses
        else:
            return []

    def process_balance(self,
                        addresses: list,
                        asset)  -> list:

        db_filepath = self.config['assets'][asset]['db_filepath']
        db_ver = 0
        if 'v1' in os_path.basename(db_filepath).lower():
            db_ver = 1
        if 'v2' in os_path.basename(db_filepath).lower():
            db_ver = 2
        db_wrapper = db_wrapper_selector(db_ver)()
        if not db_wrapper:
            self.print_payload.append(['error',
                                       'INCOMPATIBLE DB'])

        db_wrapper.connect_to_db(db_filepath=db_filepath)

        total_coin_balance = 0
        total_coin_spent = 0

        to_return = []

        for wallet_addr in addresses:

            to_append = {}

            puzzle_hash_bytes = decode_puzzle_hash(wallet_addr)
            puzzle_hash = puzzle_hash_bytes.hex()

            rows = db_wrapper.get_coins_by_puzzlehash(puzzlehash=puzzle_hash)

            coin_spent = 0
            coin_balance = 0

            for row in rows:

                amount, spent = row

                coin_raw=int.from_bytes(amount, 'big')
                parsed_coin=coin_raw/self.config['assets'][asset]['denominator']
                is_coin_spent = spent
                if is_coin_spent:
                    coin_spent += parsed_coin
                    total_coin_spent += parsed_coin
                else:
                    coin_balance += parsed_coin
                    total_coin_balance += parsed_coin

            to_append['wallet_addr'] = wallet_addr
            to_append['coin_spent'] = coin_spent
            to_append['coin_balance'] = coin_balance
            to_return.append(to_append)

        table = [[
                  entry['wallet_addr'],
                  entry['coin_balance'],
                  entry['coin_spent']
                  ] for entry in to_return]
        self.print_payload.append(['info',
                                   'Balance for each address:\n{}'.format(tabulate(table, ['Wallet',
                                                                                'Available Balance',
                                                                                'Spent Coins'], tablefmt="grid"))])
        self.print_payload.append(['info',
                                   'TOTAL: available coins:{}, spent coins:{},'.format(total_coin_balance,
                                                                          total_coin_spent)])

        return {'data': to_return,
                'message_payload': self.print_payload}

    def process_balance_CATS_only(self,
                                  addresses: list,
                                  asset)  -> list:

        if asset not in self.config['CATs'].keys():
            self.print_payload.append(['error',
                                       f"No CATs definition found for { asset }"])
            return {'data': {},
                    'message_payload': self.print_payload}

        # generate CATs wrapped addresses
        all_CAT_addrs = {}
        for CAT_info in self.config['CATs'][asset].items():
            all_CAT_addrs[CAT_info[0]] = []
            for address in addresses:
                all_CAT_addrs[CAT_info[0]].append({'vanilla_addr': address,
                                                  'wrapped_addr': self._encode_puzzle_hash(get_brun_output(asset_ID=CAT_info[1]['ID'],
                                                                                                            ph = self._decode_puzzle_hash(address)),
                                                                                                            prefix=asset.lower())})

        db_filepath = self.config['assets'][asset]['db_filepath']
        db_ver = 0
        if 'v1' in os_path.basename(db_filepath).lower():
            db_ver = 1
        if 'v2' in os_path.basename(db_filepath).lower():
            db_ver = 2
        db_wrapper = db_wrapper_selector(db_ver)()
        if not db_wrapper:
            self.print_payload.append(['error',
                                       'INCOMPATIBLE DB'])

        db_wrapper.connect_to_db(db_filepath=db_filepath)

        to_return = {}

        for CAT in all_CAT_addrs.items():
            for CAT_addrs in CAT[1]:
                if CAT[0] not in to_return.keys():
                    to_return[CAT[0]] = []

                wallet_addr = CAT_addrs['wrapped_addr']

                to_append = {}

                puzzle_hash_bytes = decode_puzzle_hash(wallet_addr)
                puzzle_hash = puzzle_hash_bytes.hex()

                rows = db_wrapper.get_coins_by_puzzlehash(puzzlehash=puzzle_hash)

                coin_spent = 0
                coin_balance = 0

                for row in rows:

                    amount, spent = row

                    coin_raw=int.from_bytes(amount, 'big')
                    parsed_coin=coin_raw/self.config['CATs'][asset][CAT[0]]['denominator']
                    is_coin_spent = spent
                    if is_coin_spent:
                        coin_spent += parsed_coin
                    else:
                        coin_balance += parsed_coin

                to_append['wallet_addr'] = wallet_addr
                to_append['coin_spent'] = coin_spent
                to_append['coin_balance'] = coin_balance
                to_return[CAT[0]].append(to_append)

        final_str = ''

        for appended_data in to_return.items():
            final_str += '\n'*4 + tabulate(tabular_data = [[entry['wallet_addr'],
                                                  entry['coin_balance'],
                                                  entry['coin_spent']] for entry in appended_data[1]],
                                          headers = [f"{ self.config['CATs'][asset][appended_data[0]]['friendly_name'] } aka { appended_data[0] } Wallet",
                                                      'Available Balance',
                                                      'Spent Coins'],
                                          tablefmt="grid")
            final_str += '\n' + f"TOTAL balance: {sum([x['coin_balance'] for x in appended_data[1]])}" \
                                f"\nTOTAL spent: {sum([x['coin_spent'] for x in appended_data[1]])}"

        self.print_payload.append(['info',
                                   'Balance for each CAT:\n{}'.format(final_str)])

        return {'data': to_return,
                'message_payload': self.print_payload}

    def return_total_balance(self,
                             addresses: list,
                             asset,
                             cats_only: bool) -> list:

        if not cats_only:
            return self.process_balance(addresses = addresses,
                                        asset = asset)
        else:
            return self.process_balance_CATS_only(addresses = addresses,
                                                  asset = asset)

    def check_mnemonic_integrity(self,
                                 mnemonic: str):
        if mnemonic == '':
            self.print_payload.append(['error',
                                       'Please input a non-empty mnemonic !'])
            return False
        if mnemonic.count(' ') != 23:
            self.print_payload.append(['error',
                                       'Your mnemonic appears to NOT have the exact number of words !'])
            return False

        return True
