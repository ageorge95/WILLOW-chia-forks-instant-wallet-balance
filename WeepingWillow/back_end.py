import sys
from os import path
from json import load,\
    dump
from traceback import format_exc
from logging import getLogger,\
    WARNING
getLogger("urllib3").setLevel(WARNING)
from chia_rs import AugSchemeMPL,\
    PrivateKey,\
    G1Element
from io import StringIO
from tabulate import tabulate
from datetime import datetime, timedelta
from decimal import Decimal
from clvm_tools.cmds import brun
from WeepingWillow.config import initial_config
from WeepingWillow.base import db_wrapper_selector,\
    config_handler
from chia.wallet.puzzles.p2_delegated_puzzle_or_hidden_puzzle import puzzle_for_pk
from chia.wallet.derive_keys import master_sk_to_farmer_sk
from chia.util.keychain import mnemonic_to_seed
from chia.util.byte_types import hexstr_to_bytes
from chia.util.bech32m import encode_puzzle_hash,\
    decode_puzzle_hash

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

class WILLOW_back_end(config_handler):

    def __init__(self):

        self._log = getLogger()

        super(WILLOW_back_end, self).__init__()

    def return_addresses(self,
                         mnemonic: str,
                         prefix: str,
                         asset: str,
                         nr_of_addresses: int = 500) -> dict:

        all_addresses = {'hardened': [],
                         'unhardened': [],
                         'farmeraddr': ''}

        if self.check_mnemonic_integrity(mnemonic):

            seed: bytes = mnemonic_to_seed(mnemonic)
            master_sk: PrivateKey = AugSchemeMPL.key_gen(seed)
            farmer_sk: PrivateKey = master_sk_to_farmer_sk(master_sk)
            farmer_pk: G1Element = farmer_sk.get_g1()

            # generate farmer address
            self._log.info(f"Generating the farmer address based on the provided mnemonic. Please wait ...")
            try:
                puzzle = puzzle_for_pk(farmer_pk)
                puzzle_hash = puzzle.get_tree_hash()
                farmer_address = encode_puzzle_hash(puzzle_hash, prefix)
                all_addresses['farmeraddr'] = farmer_address
                self._log.info('Farmer address generated successfully !')

            except:
                self._log.error(f"Oh snap ! There was an error while generating the farmer address:\n{format_exc(chain=False)}")

            # generate hardened addresses
            for derivation_port in self.config["assets"][asset]['wallet_sk_derivation_port']:
                self._log.info(f"Generating {nr_of_addresses} hardened addresses based on the provided mnemonic via {derivation_port} derivation port. Please wait ...")
                try:

                    wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk(master_sk, 12381)
                    wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk(wallet_sk_intermediate, derivation_port)
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
                self._log.info(f"Generating {nr_of_addresses} unhardened addresses based on the provided mnemonic via {derivation_port} derivation port. Please wait ...")
                try:

                    # unhardened public keys
                    wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk_unhardened(master_sk, 12381)
                    wallet_sk_intermediate: PrivateKey = AugSchemeMPL.derive_child_sk_unhardened(wallet_sk_intermediate, derivation_port)
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

                coin_spent = Decimal('0')
                coin_balance = Decimal('0')

                for row in rows:

                    timestamp, amount, spent = row

                    coin_raw=Decimal(str(int.from_bytes(amount, 'big', signed=True)))
                    parsed_coin=coin_raw/Decimal(str(self.config['assets'][asset]['denominator']))
                    is_coin_spent = spent
                    if is_coin_spent:
                        coin_spent += parsed_coin
                        to_return['total_coin_spent'] += parsed_coin
                    else:
                        coin_balance += parsed_coin
                        to_return['total_coin_balance'] += parsed_coin

                    to_return['transactions'].append({'timestamp': timestamp,
                                                      'amount': parsed_coin,
                                                      'is_coin_spent': is_coin_spent,
                                                      'wallet': wallet_addr})

                to_return['address_info'].append({'wallet_addr': wallet_addr,
                                                  'coin_spent': coin_spent,
                                                  'coin_balance': coin_balance})
        except:
            self._log.error(f"Failed to execute process_balance. Reason:\n{format_exc(chain=False)}")

        # sort the transactions returned data time-wise
        to_return['transactions'] = sorted(to_return['transactions'], key=lambda _:_['timestamp'],
                                           reverse=True)
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

                for CAT_addrs in vanilla_wrapped_addrs:
                    coin_spent = Decimal('0')
                    coin_balance = Decimal('0')

                    if CAT_name not in to_return.keys():
                        to_return[CAT_name] = {'address_info': [],
                                               'total_coin_balance': Decimal('0'),
                                               'total_coin_spent': Decimal('0'),
                                               'transactions': []}

                    wrapped_addr = CAT_addrs['wrapped_addr']

                    puzzle_hash_bytes = decode_puzzle_hash(wrapped_addr)
                    puzzle_hash = puzzle_hash_bytes.hex()

                    rows = db_wrapper.get_coins_by_puzzlehash(puzzlehash=puzzle_hash)

                    for row in rows:

                        timestamp, amount, spent = row

                        coin_raw=Decimal(str(int.from_bytes(amount, 'big')))
                        parsed_coin=coin_raw/Decimal(str(self.config['CATs'][asset][CAT_name]['denominator']))
                        is_coin_spent = spent
                        if is_coin_spent:
                            to_return[CAT_name]['total_coin_spent'] += parsed_coin
                            coin_spent += parsed_coin
                        else:
                            to_return[CAT_name]['total_coin_balance'] += parsed_coin
                            coin_balance += parsed_coin

                        to_return[CAT_name]['transactions'].append({'timestamp': timestamp,
                                                                    'amount': parsed_coin,
                                                                    'is_coin_spent': is_coin_spent,
                                                                    'wallet': wrapped_addr})

                    to_return[CAT_name]['address_info'].append({'wallet_addr': wrapped_addr,
                                                                'coin_spent': coin_spent,
                                                                'coin_balance': coin_balance})
        except:
            self._log.error(f"Failed to execute process_balance_CATS_only. Reason:\n{format_exc(chain=False)}")

        return to_return

    def return_last_block_win_ts(self,
                                 asset: str,
                                 addresses: list = None,
                                 mnemonic: str = None,
                                 prefix: str = None,
                                 nr_of_addresses: int = 500) -> None:

        if mnemonic:

            addresses = self.return_addresses(mnemonic=mnemonic,
                                              prefix=prefix,
                                              asset=asset,
                                              nr_of_addresses=nr_of_addresses)
            addresses = addresses['hardened'] + addresses['unhardened']

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

            last_win_ts = 0
            for wallet_addr in addresses:

                puzzle_hash_bytes = decode_puzzle_hash(wallet_addr)
                puzzle_hash = puzzle_hash_bytes.hex()

                rows = db_wrapper.get_last_win_time(puzzlehash=puzzle_hash)
                if rows:
                    if rows[0][0] > last_win_ts:
                        last_win_ts = rows[0][0]

            self._log.info(f'Last win timestamp is ${last_win_ts}${datetime.utcfromtimestamp(last_win_ts)}$')

        except:
            self._log.error(f"Failed to execute return_last_block_win_ts. Reason:\n{format_exc(chain=False)}")

    def return_balance_statistics(self,
                                 asset: str,
                                 addresses: list = None,
                                 mnemonic: str = None,
                                 prefix: str = None,
                                 nr_of_addresses: int = 500) -> None:
        if mnemonic:

            addresses = self.return_addresses(mnemonic=mnemonic,
                                              prefix=prefix,
                                              asset=asset,
                                              nr_of_addresses=nr_of_addresses)
            addresses = addresses['hardened'] + addresses['unhardened']
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

            all_coins = []
            for wallet_addr in addresses:
                puzzle_hash_bytes = decode_puzzle_hash(wallet_addr)
                puzzle_hash = puzzle_hash_bytes.hex()

                all_coins += db_wrapper.get_coins_by_puzzlehash(puzzle_hash)

            final_data_store = {}
            for task in {'AVAILABLE_ALL_TIME': 0,
                         'AVAILABLE_30_DAY': (datetime.now() - timedelta(days=30)).timestamp(),
                         'AVAILABLE_7_DAY': (datetime.now() - timedelta(days=7)).timestamp(),
                         'AVAILABLE_3_DAY': (datetime.now() - timedelta(days=3)).timestamp(),
                         'AVAILABLE_1_DAY': (datetime.now() - timedelta(days=1)).timestamp()}.items():
                final_data_store[task[0]] = str(sum([Decimal(str(int.from_bytes(_[1], 'big', signed=True)))
                                                 for _ in list(filter(lambda _:
                                                                      _[0] > task[1] and not _[2],
                                                                      all_coins))])\
                                            /Decimal(str(self.config['assets'][asset]['denominator'])))
            for task in {'INCOME_ALL_TIME': 0,
                         'INCOME_30_DAY': (datetime.now() - timedelta(days=30)).timestamp(),
                         'INCOME_7_DAY': (datetime.now() - timedelta(days=7)).timestamp(),
                         'INCOME_3_DAY': (datetime.now() - timedelta(days=3)).timestamp(),
                         'INCOME_1_DAY': (datetime.now() - timedelta(days=1)).timestamp()}.items():
                final_data_store[task[0]] = str(sum([Decimal(str(int.from_bytes(_[1], 'big', signed=True)))
                                                 for _ in list(filter(lambda _:
                                                                      _[0] > task[1],
                                                                      all_coins))])\
                                            /Decimal(str(self.config['assets'][asset]['denominator'])))
            for task in {'SPENT_ALL_TIME': 0,
                         'SPENT_30_DAY': (datetime.now() - timedelta(days=30)).timestamp(),
                         'SPENT_7_DAY': (datetime.now() - timedelta(days=7)).timestamp(),
                         'SPENT_3_DAY': (datetime.now() - timedelta(days=3)).timestamp(),
                         'SPENT_1_DAY': (datetime.now() - timedelta(days=1)).timestamp()}.items():
                final_data_store[task[0]] = str(sum([Decimal(str(int.from_bytes(_[1], 'big', signed=True)))
                                                 for _ in list(filter(lambda _:
                                                                      _[0] > task[1] and _[2],
                                                                      all_coins))])\
                                            /Decimal(str(self.config['assets'][asset]['denominator'])))

            for task in {'AVAILABLE_COINS_COUNT_ALL_TIME': 0,
                         'AVAILABLE_COINS_COUNT_30_DAY': (datetime.now() - timedelta(days=30)).timestamp(),
                         'AVAILABLE_COINS_COUNT_7_DAY': (datetime.now() - timedelta(days=7)).timestamp(),
                         'AVAILABLE_COINS_COUNT_3_DAY': (datetime.now() - timedelta(days=3)).timestamp(),
                         'AVAILABLE_COINS_COUNT_1_DAY': (datetime.now() - timedelta(days=1)).timestamp()}.items():
                final_data_store[task[0]] = len(list(filter(lambda _:_[0] > task[1] and not _[2], all_coins)))

            self._log.info(f'Balance statistics result:${str(final_data_store)}$')

        except:
            self._log.error(f"Failed to execute return_balance_statistics. Reason:\n{format_exc(chain=False)}")

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
                        custom_addresses: list = None,
                        transactions_limit: int = 20):

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
            total_coin_balance = Decimal('0')
            total_coin_spent = Decimal('0')

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

                table = [[
                       datetime.fromtimestamp(entry['timestamp']),
                       f"\x1b[31;1m- {entry['amount']}\x1b[0m" if entry['is_coin_spent'] else
                           f"\x1b[32;1m+ {entry['amount']}\x1b[0m",
                       bool(entry['is_coin_spent']),
                       entry['wallet']
                  ] for entry in balance[addr_type]['transactions'][:transactions_limit]]

                self._log.info(f"Transactions history for all $${addr_type}$$ addresses:\n"
                               f"{tabulate(table, ['Timestamp', 'Balance', 'Spent', 'Affected wallet'], tablefmt='grid')}")

                self._log.info(f"TOTAL: available amount:{total_coin_balance}, spent amount:{total_coin_spent}")

        else:
            total_coin_balance = {}
            total_coin_spent = {}

            for addr_type in types_to_show:
                for CAT in balance[addr_type].keys():

                    if CAT not in total_coin_balance.keys():
                        total_coin_balance[CAT] = Decimal('0')
                        total_coin_spent[CAT] = Decimal('0')

                    tabular_data = []
                    for appended_data in balance[addr_type][CAT]['address_info']:
                        tabular_data.append([appended_data['wallet_addr'],
                                             appended_data['coin_balance'],
                                             appended_data['coin_spent']])

                    final_str = f"$${addr_type}$$ CATs balance for {CAT} -> {self.config['CATs'][asset][CAT]['friendly_name']}\n" + \
                                 tabulate(tabular_data = tabular_data,
                                          headers = [f"Wallet Addr",
                                                     'Available Balance',
                                                     'Spent Coins'],
                                          tablefmt="grid")

                    tabular_data = []
                    for appended_data in balance[addr_type][CAT]['transactions'][:transactions_limit]:
                        tabular_data.append([datetime.fromtimestamp(appended_data['timestamp']),
                                             f"\x1b[31;1m- {appended_data['amount']}\x1b[0m" if appended_data['is_coin_spent'] else
                                                f"\x1b[32;1m+ {appended_data['amount']}\x1b[0m",
                                             bool(appended_data['is_coin_spent']),
                                             appended_data['wallet']])

                    final_str += f"\nTransactions for {CAT} -> {self.config['CATs'][asset][CAT]['friendly_name']}\n" + \
                                 tabulate(tabular_data = tabular_data,
                                          headers = [f"Timestamp",
                                                     'Balance',
                                                     'Spent',
                                                     'Affected Wallet'],
                                          tablefmt="grid")

                    final_str += '\n' + f"TOTAL balance: {balance[addr_type][CAT]['total_coin_balance']}" \
                                        f"\nTOTAL spent: {balance[addr_type][CAT]['total_coin_spent']}"

                    self._log.info(final_str + '\n'*4)

# For debugging purposes
# You can use this piece of code yourself either in your scripts or directly by running this script
if __name__ == '__main__':
    from base import configure_logger_and_queue
    configure_logger_and_queue()

    my_obj = WILLOW_back_end()
    my_obj.exec_full_cycle(mnemonic='',
                           prefix='xcc',
                           asset='XCC',
                           cats_only=False,
                           nr_of_addresses=5,
                           custom_addresses=['xcc1amn5txlltvlcnlt6auw24ys6xku7t3npqt2szllassymswnehepszhnjar'],
                           )