import sys
from os import path
from json import load,\
    dump
from traceback import format_exc
from logging import getLogger,\
    WARNING
getLogger("urllib3").setLevel(WARNING)
sys.path.insert(0,path.join(path.dirname(__file__)))
sys.path.insert(0,path.join(path.dirname(__file__), 'chia_blockchain'))
from chia_blockchain.chia.util.keychain import mnemonic_to_seed
from chia_blockchain.chia.util.byte_types import hexstr_to_bytes
from chia_blockchain.chia.util.bech32m import encode_puzzle_hash,\
    decode_puzzle_hash
from blspy import AugSchemeMPL,\
    PrivateKey,\
    G1Element
from _00_config import initial_config
from _00_WILLOW_base import db_wrapper_selector
from io import StringIO
from clvm_tools.cmds import brun
from chia_blockchain.chia.wallet.puzzles.p2_delegated_puzzle_or_hidden_puzzle import puzzle_for_pk
from tabulate import tabulate

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
        brun(["",
              "(a (q 2 30 (c 2 (c 5 (c 23 (c (sha256 28 11) (c (sha256 28 5) ()))))))"
                  " (c (q (a 4 . 1) (q . 2) (a (i 5 (q 2 22 (c 2 (c 13 (c (sha256 26 (sha256 28 20)"
                  " (sha256 26 (sha256 26 (sha256 28 18) 9) (sha256 26 11 (sha256 28 ())))) ())))) (q . 11)) 1)"
                  " 11 26 (sha256 28 8) (sha256 26 (sha256 26 (sha256 28 18) 5)"
                  " (sha256 26 (a 22 (c 2 (c 7 (c (sha256 28 28) ())))) (sha256 28 ())))) 1))",
              "(0x72dec062874cd4d3aab892a0906688a1ae412b0109982e1797a170add88bdcdc"
                  f" 0x{asset_ID}"
                  f" 0x{ph})"])
    return output[0]

class WILLOW_back_end():

    def __init__(self):

        self._log = getLogger()

        config_path = 'config_willow.json' if '_MEIPASS' in sys.__dict__\
                                           else path.join(path.dirname(__file__),'config_willow.json')
        if path.isfile(config_path):
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

    def return_addresses(self,
                         mnemonic: str,
                         prefix: str,
                         asset: str,
                         nr_of_addresses: int = 500) -> dict:

        all_addresses = {'hardened': [],
                         'unhardened': []}

        if self.check_mnemonic_integrity(mnemonic):

            seed: bytes = mnemonic_to_seed(mnemonic, passphrase="")
            master_sk: PrivateKey = AugSchemeMPL.key_gen(seed)

            # generate hardened addresses
            self._log.info(f"Generating {nr_of_addresses} hardened addresses based on the provided mnemonic. Please wait ...")
            try:

                wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk(master_sk, 12381)
                wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk(wallet_sk_intermediate, self.config["assets"][asset]['wallet_sk_derivation_port'])
                wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk(wallet_sk_intermediate, 2)
                for i in range(nr_of_addresses):
                    child_sk: PrivateKey = AugSchemeMPL.derive_child_sk(wallet_sk_intermediate, i)
                    child_pk: G1Element = child_sk.get_g1()
                    puzzle = puzzle_for_pk(child_pk)
                    puzzle_hash = puzzle.get_tree_hash()
                    address = encode_puzzle_hash(puzzle_hash, prefix)
                    all_addresses['hardened'].append(address)

                self._log.info('Hardened addresses generated successfully !')

            except:
                self._log.error(f"Oh snap ! There was an error while generating the hardened addresses:\n{format_exc(chain=False)}")

            # generate unhardened addresses
            self._log.info(f"Generating {nr_of_addresses} unhardened addresses based on the provided mnemonic. Please wait ...")
            try:

                # unhardened public keys
                wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk_unhardened(master_sk, 12381)
                wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk_unhardened(wallet_sk_intermediate, self.config["assets"][asset]['wallet_sk_derivation_port'])
                wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk_unhardened(wallet_sk_intermediate, 2)
                for i in range(nr_of_addresses):
                    child_sk: PrivateKey = AugSchemeMPL.derive_child_sk_unhardened(wallet_sk_intermediate, i)
                    child_pk: G1Element = child_sk.get_g1()
                    puzzle = puzzle_for_pk(child_pk)
                    puzzle_hash = puzzle.get_tree_hash()
                    address = encode_puzzle_hash(puzzle_hash, prefix)
                    all_addresses['unhardened'].append(address)

                self._log.info('Unhardened addresses generated successfully !')

            except:
                self._log.error(f"Oh snap ! There was an error while generating the unhardened addresses:\n{format_exc(chain=False)}")

        return all_addresses

    def process_balance(self,
                        addresses: list,
                        asset) -> dict:

        to_return = {'address_info': [],
                     'total_coin_balance': 0,
                     'total_coin_spent': 0,
                     'transactions': []}

        try:

            db_filepath = self.config['assets'][asset]['db_filepath']
            db_ver = 0
            if 'v1' in path.basename(db_filepath).lower():
                db_ver = 1
            if 'v2' in path.basename(db_filepath).lower():
                db_ver = 2
            db_wrapper = db_wrapper_selector(db_ver)()
            if not db_wrapper:
                self._log.error(f"INCOMPATIBLE DB: {db_filepath}")
                raise Exception(f"INCOMPATIBLE DB: {db_filepath}")

            db_wrapper.connect_to_db(db_filepath=db_filepath)

            for wallet_addr in addresses:

                puzzle_hash_bytes = decode_puzzle_hash(wallet_addr)
                puzzle_hash = puzzle_hash_bytes.hex()

                rows = db_wrapper.get_coins_by_puzzlehash(puzzlehash=puzzle_hash)

                coin_spent = 0
                coin_balance = 0

                for row in rows:

                    timestamp, amount, spent = row

                    coin_raw=int.from_bytes(amount, 'big')
                    parsed_coin=coin_raw/self.config['assets'][asset]['denominator']
                    is_coin_spent = spent
                    if is_coin_spent:
                        coin_spent += parsed_coin
                        to_return['total_coin_spent'] += parsed_coin
                    else:
                        coin_balance += parsed_coin
                        to_return['total_coin_balance'] += parsed_coin

                    to_return['transactions'].append({'timestamp': timestamp,
                                                      'amount': parsed_coin,
                                                      'is_coin_spent': is_coin_spent})

                to_return['address_info'].append({'wallet_addr': wallet_addr,
                                                  'coin_spent': coin_spent,
                                                  'coin_balance': coin_balance})
        except:
            self._log.error(f"Failed to execute process_balance. Reason:\n{format_exc(chain=False)}")

        return to_return

    def process_balance_CATS_only(self,
                                  addresses: list,
                                  asset) -> dict:

        all_CAT_addrs = {}
        to_return = {}

        try:

            if asset not in self.config['CATs'].keys():
                self._log.error(f"No CATs definition found for { asset }")
                raise Exception(f"No CATs definition found for { asset }")

            # generate CATs wrapped addresses
            for CAT_info in self.config['CATs'][asset].items():
                all_CAT_addrs[CAT_info[0]] = []
                for address in addresses:
                    all_CAT_addrs[CAT_info[0]].append({'vanilla_addr': address,
                                                       'wrapped_addr': encode_puzzle_hash(hexstr_to_bytes(get_brun_output(asset_ID=CAT_info[1]['ID'],
                                                                                                                          ph = decode_puzzle_hash(address))),
                                                                                                                          prefix=asset.lower())})

            db_filepath = self.config['assets'][asset]['db_filepath']
            db_ver = 0
            if 'v1' in path.basename(db_filepath).lower():
                db_ver = 1
            if 'v2' in path.basename(db_filepath).lower():
                db_ver = 2
            db_wrapper = db_wrapper_selector(db_ver)()
            if not db_wrapper:
                self._log.error(f"INCOMPATIBLE DB: {db_filepath}")
                raise Exception(f"INCOMPATIBLE DB: {db_filepath}")

            db_wrapper.connect_to_db(db_filepath=db_filepath)

            for CAT_name, vanilla_wrapped_addrs in all_CAT_addrs.items():
                total_coin_spent = 0
                total_coin_balance = 0

                for CAT_addrs in vanilla_wrapped_addrs:
                    coin_spent = 0
                    coin_balance = 0

                    if CAT_name not in to_return.keys():
                        to_return[CAT_name] = {'address_info': [],
                                               'total_coin_balance': 0,
                                               'total_coin_spent': 0,
                                               'transactions': []}

                    wrapped_addr = CAT_addrs['wrapped_addr']

                    puzzle_hash_bytes = decode_puzzle_hash(wrapped_addr)
                    puzzle_hash = puzzle_hash_bytes.hex()

                    rows = db_wrapper.get_coins_by_puzzlehash(puzzlehash=puzzle_hash)

                    for row in rows:

                        timestamp, amount, spent = row

                        coin_raw=int.from_bytes(amount, 'big')
                        parsed_coin=coin_raw/self.config['CATs'][asset][CAT_name]['denominator']
                        is_coin_spent = spent
                        if is_coin_spent:
                            to_return[CAT_name]['total_coin_spent'] += parsed_coin
                            coin_spent += parsed_coin
                        else:
                            to_return[CAT_name]['total_coin_balance'] += parsed_coin
                            coin_balance += parsed_coin

                        to_return[CAT_name]['transactions'].append({'timestamp': timestamp,
                                                                    'amount': parsed_coin,
                                                                    'is_coin_spent': is_coin_spent})

                    to_return[CAT_name]['address_info'].append({'wallet_addr': wrapped_addr,
                                                                'coin_spent': coin_spent,
                                                                'coin_balance': coin_balance})
        except:
            self._log.error(f"Failed to execute process_balance_CATS_only. Reason:\n{format_exc(chain=False)}")

        return to_return

    def return_total_balance(self,
                             addresses: list,
                             asset,
                             cats_only: bool) -> dict:

        if not cats_only:
            return self.process_balance(addresses = addresses,
                                        asset = asset)
        else:
            return self.process_balance_CATS_only(addresses = addresses,
                                                  asset = asset)

    def check_mnemonic_integrity(self,
                                 mnemonic: str):
        if mnemonic == '':
            self._log.error('Please input a non-empty mnemonic !')
            return False
        if mnemonic.count(' ') != 23:
            self._log.error('Your mnemonic appears to NOT have the exact number of words !')
            return False

        return True

    def exec_full_cycle(self,
                        mnemonic: str,
                        prefix: str,
                        asset: str,
                        cats_only: bool,
                        nr_of_addresses: int = 500,
                        custom_addresses: list = None
                        ):

        # compute the required addresses. if needed
        balance = {}
        if not custom_addresses:
            types_to_show = ['hardened', 'unhardened']
        else:
            types_to_show = ['custom']

        if not custom_addresses:
            custom_addresses = self.return_addresses(mnemonic=mnemonic,
                                              prefix=prefix,
                                              asset=asset,
                                              nr_of_addresses=nr_of_addresses)

            # compute the balance for all the hardened/ unhardened addresses, if a mnemonic is provided
            for addr_type in types_to_show:

                if not cats_only:
                    balance[addr_type] = self.process_balance(addresses = custom_addresses[addr_type],
                                                              asset = asset)
                else:
                    balance[addr_type] = self.process_balance_CATS_only(addresses = custom_addresses[addr_type],
                                                                        asset = asset)

        # compute the balance only for the addresses provided direclty by the user, without the mnemonic
        else:
            for addr_type in types_to_show:
                if not cats_only:
                    balance[addr_type] = self.process_balance(addresses = custom_addresses,
                                                              asset = asset)
                else:
                    balance[addr_type] = self.process_balance_CATS_only(addresses = custom_addresses,
                                                                        asset = asset)

        # print the results
        if not cats_only:
            total_coin_balance = 0
            total_coin_spent = 0

            for addr_type in types_to_show:

                total_coin_balance += balance[addr_type]['total_coin_balance']
                total_coin_spent += balance[addr_type]['total_coin_spent']

                table = [[
                  entry['wallet_addr'],
                  entry['coin_balance'],
                  entry['coin_spent']
                  ] for entry in balance[addr_type]['address_info']]

                self._log.info(f"Balance for each $${addr_type}$$ address:\n"
                               f"{tabulate(table, ['Wallet', 'Available Balance', 'Spent Coins'], tablefmt='grid')}")

                self._log.info(f"TOTAL: available coins:{total_coin_balance}, spent coins:{total_coin_spent}")

        else:
            total_coin_balance = {}
            total_coin_spent = {}

            for addr_type in types_to_show:
                for CAT in balance[addr_type].keys():

                    if CAT not in total_coin_balance.keys():
                        total_coin_balance[CAT] = 0
                        total_coin_spent[CAT] = 0

                    final_str = f"Showing the {addr_type} CATs balance for {CAT} -> {self.config['CATs'][asset][CAT]['friendly_name']}\n"

                    tabular_data = []
                    for appended_data in balance[addr_type][CAT]['address_info']:
                        tabular_data.append([appended_data['wallet_addr'],
                                             appended_data['coin_balance'],
                                             appended_data['coin_spent']])

                    final_str += tabulate(tabular_data = tabular_data,
                                          headers = [f"Wallet Addr",
                                                     'Available Balance',
                                                     'Spent Coins'],
                                          tablefmt="grid")
                    final_str += '\n' + f"TOTAL balance: {balance[addr_type][CAT]['total_coin_balance']}" \
                                        f"\nTOTAL spent: {balance[addr_type][CAT]['total_coin_spent']}"

                    self._log.info(final_str + '\n'*4)

# For debugging purposes
# You can use this piece of code yourself either in your scripts or directly by running this script
if __name__ == '__main__':
    from _00_WILLOW_base import configure_logger_and_queue
    configure_logger_and_queue()

    my_obj = WILLOW_back_end()
    my_obj.exec_full_cycle(mnemonic='',
                           prefix='xcc',
                           asset='XCC',
                           cats_only=True,
                           nr_of_addresses=5,
                           custom_addresses=['xcc1amn5txlltvlcnlt6auw24ys6xku7t3npqt2szllassymswnehepszhnjar'],
                           )