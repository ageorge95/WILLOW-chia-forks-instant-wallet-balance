from sqlite3 import connect
from logging import getLogger
from json import load,\
    dump
from tabulate import tabulate
from traceback import format_exc
import sys
from os import path as os_path
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

    def return_total_balance(self,
                             addresses: list,
                             coin) -> list:

        db_filepath = self.config[coin]['db_filepath']
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
                parsed_coin=coin_raw/self.config[coin]['denominator']
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

    def check_mnemonic_integrity(self,
                                 mnemonic: str):
        if mnemonic == '':
            self.print_payload.append(['warning',
                                              'Please input a non-empty mnemonic !'])
            return False
        if mnemonic.count(' ') != 23:
            self.print_payload.append(['warning',
                                              'Your mnemonic appears to NOT have the exact number of words !'])
            return False

        return True

    def get_balance(self,
                    input: list,
                    coin: str,
                    method: str):
        if method == 'via_mnemonic':
            if not self.check_mnemonic_integrity(input[0]):
                return
            input = self.return_addresses(mnemonic=input[0],
                                          prefix=coin.lower())

        self.return_total_balance(addresses=input,
                                  coin=coin)
