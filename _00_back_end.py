from sqlite3 import connect
from logging import getLogger
from json import load,\
    dump
from tabulate import tabulate
from traceback import format_exc
from sys import path
from os import path as os_path
path.append(os_path.join(os_path.dirname(__file__)))
path.append(os_path.join(os_path.dirname(__file__), 'chia_blockchain'))

from chia_blockchain.chia.util.keychain import mnemonic_to_seed
from chia_blockchain.chia.util.bech32m import encode_puzzle_hash,\
    decode_puzzle_hash
from chia_blockchain.chia.consensus.coinbase import create_puzzlehash_for_pk
from chia_blockchain.chia.util.ints import uint32
from blspy import AugSchemeMPL
from chia_blockchain.chia.wallet.derive_keys import master_sk_to_wallet_sk

initial_config = {'AEC': {'db_filepath': '{userdir}\\.aedge\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'aedge'},
                 'APPLE': {'db_filepath': '{userdir}\\.apple\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                           'denominator': 1000000000000,
                           'friendly_name': 'apple'},
                 'AVO': {'db_filepath': '{userdir}\\.avocado\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'avocado'},
                 'CAC': {'db_filepath': '{userdir}\\.cactus\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'cactus'},
                 'CANS': {'db_filepath': '{userdir}\\.cannabis\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000000,
                          'friendly_name': 'cannabis'},
                 'CGN': {'db_filepath': '{userdir}\\.chaingreen\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'chaingreen'},
                 'COV': {'db_filepath': '{userdir}\\.covid\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'covid'},
                 'GDOG': {'db_filepath': '{userdir}\\.greendoge\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000000,
                          'friendly_name': 'greendoge'},
                 'HDD': {'db_filepath': '{userdir}\\.hddcoin\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'hddcoin'},
                 'LCH': {'db_filepath': '{userdir}\\.lotus\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'lotus'},
                 'MELON': {'db_filepath': '{userdir}\\.melon\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                           'denominator': 1000000000,
                           'friendly_name': 'melon'},
                 'MGA': {'db_filepath': '{userdir}\\.mogua\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'mogua'},
                 'NCH': {'db_filepath': '{userdir}\\.chia\\ext9\\db\\blockchain_v1_ext9.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'n-chain_ext9'},
                 'OZT': {'db_filepath': '{userdir}\\.goldcoin\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'Goldcoin'},
                 'PEA': {'db_filepath': '{userdir}\\.peas\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'peas'},
                 'PIPS': {'db_filepath': '{userdir}\\.pipscoin\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000000,
                          'friendly_name': 'Pipscoin'},
                 'ROLLS': {'db_filepath': '{userdir}\\.rolls\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                           'denominator': 1000000000000,
                           'friendly_name': 'rolls'},
                 'SCM': {'db_filepath': '{userdir}\\.scam\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'Scamcoin'},
                 'SIT': {'db_filepath': '{userdir}\\.sit\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'silicoin'},
                 'SIX': {'db_filepath': '{userdir}\\.lucky\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'lucky'},
                 'SOCK': {'db_filepath': '{userdir}\\.socks\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000000,
                          'friendly_name': 'socks'},
                 'SPARE': {'db_filepath': '{userdir}\\.spare-blockchain\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                           'denominator': 1000000000000,
                           'friendly_name': 'spare'},
                 'STAI': {'db_filepath': '{userdir}\\.staicoin\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000,
                          'friendly_name': 'staicoin'},
                 'STOR': {'db_filepath': '{userdir}\\.stor\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000000,
                          'friendly_name': 'stor'},
                 'TAD': {'db_filepath': '{userdir}\\.tad\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'tad'},
                 'TRZ': {'db_filepath': '{userdir}\\.tranzact\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'tranzact'},
                 'WHEAT': {'db_filepath': '{userdir}\\.wheat\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                           'denominator': 1000000000000,
                           'friendly_name': 'wheat'},
                 'XBR': {'db_filepath': '{userdir}\\.beernetwork\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'Beer'},
                 'XBT': {'db_filepath': '{userdir}\\.beet\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'Beet'},
                 'XBTC': {'db_filepath': '{userdir}\\.btcgreen\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000000,
                          'friendly_name': 'btcgreen'},
                 'XCA': {'db_filepath': '{userdir}\\.xcha\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'xcha'},
                 'XCC': {'db_filepath': '{userdir}\\.chives\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 100000000,
                         'friendly_name': 'chives'},
                 'XCD': {'db_filepath': '{userdir}\\.cryptodoge\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000,
                         'friendly_name': 'cryptodoge'},
                 'XCH': {'db_filepath': '{userdir}\\.chia\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'chia'},
                 'XCR': {'db_filepath': '{userdir}\\.chiarose\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000,
                         'friendly_name': 'chiarose'},
                 'XDG': {'db_filepath': '{userdir}\\.dogechia\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'dogechia'},
                 'XETH': {'db_filepath': '{userdir}\\.ethgreen\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000,
                          'friendly_name': 'ethgreen'},
                 'XFK': {'db_filepath': '{userdir}\\.fork\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'fork'},
                 'XFL': {'db_filepath': '{userdir}\\.flora\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'flora'},
                 'XFX': {'db_filepath': '{userdir}\\.flax\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'flax'},
                 'XKA': {'db_filepath': '{userdir}\\.kale\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'kale'},
                 'XKJ': {'db_filepath': '{userdir}\\.kujenga\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'kujenga'},
                 'XKM': {'db_filepath': '{userdir}\\.mint\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'mint'},
                 'XKW': {'db_filepath': '{userdir}\\.kiwi\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'Kiwi'},
                 'XMX': {'db_filepath': '{userdir}\\.melati\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'melati'},
                 'XMZ': {'db_filepath': '{userdir}\\.maize\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'maize'},
                 'XNT': {'db_filepath': '{userdir}\\.skynet\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'skynet'},
                 'XOL': {'db_filepath': '{userdir}\\.olive\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'olive'},
                 'XSC': {'db_filepath': '{userdir}\\.sector\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'sector'},
                 'XSHIB': {'db_filepath': '{userdir}\\.shibgreen\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                           'denominator': 1000,
                           'friendly_name': 'shibgreen'},
                 'XSLV': {'db_filepath': '{userdir}\\.salvia\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                          'denominator': 1000000000000,
                          'friendly_name': 'salvia'},
                 'XTX': {'db_filepath': '{userdir}\\.taco\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'taco'},
                 'XVM': {'db_filepath': '{userdir}\\.venidium\\mainnet\\db\\blockchain_v1_mainnet.sqlite'.format(userdir=os_path.expanduser("~")),
                         'denominator': 1000000000000,
                         'friendly_name': 'venidium'}}

class WILLOW_back_end():
    
    _log: getLogger = None

    def __init__(self):

        if not self._log:
            self._log = getLogger()

        if os_path.isfile('config_willow.json'):
            try:
                with open('config_willow.json', 'r') as json_in_handle:
                    self.config = load(json_in_handle)
            except:
                self.config = initial_config
        else:
            self.config = initial_config
            with open('config_willow.json', 'w') as json_out_handle:
                dump(self.config, json_out_handle, indent=2)

        super(WILLOW_back_end, self).__init__()

    def return_addresses(self,
                         mnemonic: str,
                         prefix: str,
                         nr_of_addresses: int = 500) -> list:

        self._log.info('Generating {} addresses based on the provided mnemonic. Please wait ...'.format(nr_of_addresses))
        all_addresses = []
        try:
            seed = mnemonic_to_seed(mnemonic=mnemonic,
                                    passphrase='')
            sk = AugSchemeMPL.key_gen(seed)

            for i in range(nr_of_addresses):
                all_addresses.append(encode_puzzle_hash(create_puzzlehash_for_pk(master_sk_to_wallet_sk(sk, uint32(i)).get_g1()), prefix))
            self._log.info('{} addresses successfully generated:\n{}'.format(nr_of_addresses,'\n'.join(all_addresses)))
        except:
            self._log.error('Oh snap ! There was an error while generating the addresses:\n{}'.format(format_exc(chain=False)))


        return all_addresses

    def return_total_balance(self,
                             addresses: list,
                             coin) -> dict:

        db_filepath = self.config[coin]['db_filepath']
        conn = connect(db_filepath)
        dbcursor = conn.cursor()

        total_coin_balance = 0
        total_coin_spent = 0

        to_return = {}

        for wallet_addr in addresses:

            to_return[wallet_addr] = {}

            puzzle_hash_bytes = decode_puzzle_hash(wallet_addr)
            puzzle_hash = puzzle_hash_bytes.hex()

            dbcursor.execute("SELECT * FROM coin_record WHERE puzzle_hash=?", (puzzle_hash,))
            rows = dbcursor.fetchall()

            coin_spent = 0
            coin_balance = 0

            for row in rows:

                coin_raw=int.from_bytes(row[7], 'big')
                parsed_coin=coin_raw/self.config[coin]['denominator']
                is_coin_spent = row[3]
                if is_coin_spent:
                    coin_spent += parsed_coin
                    total_coin_spent += parsed_coin
                else:
                    coin_balance += parsed_coin
                    total_coin_balance += parsed_coin

            to_return[wallet_addr]['coin_spent'] = coin_spent
            to_return[wallet_addr]['coin_balance'] = coin_balance

        table = [[
                  entry[0],
                  entry[1]['coin_balance'],
                  entry[1]['coin_spent']
                  ] for entry in to_return.items()]
        self._log.info('Balance for each address:\n{}'.format(tabulate(table, ['Wallet',
                                                                                'Available Balance',
                                                                                'Spent Coins'], tablefmt="grid")))
        self._log.info('TOTAL: {} available coins, {} spent coins'.format(total_coin_balance,
                                                                          total_coin_spent))

        return to_return

    def check_mnemonic_integrity(self,
                                 mnemonic: str):
        if mnemonic == '':
            self._log.warning('Please input a non-empty mnemonic !')
            return False
        if mnemonic.count(' ') != 23:
            self._log.warning('Your mnemonic appears to NOT have the exact number of words !')
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
