from sys import path,\
    exit
from os import path as os_path
path.append(os_path.join('chia_blockchain'))

import argparse
from sqlite3 import connect
from json import dump,\
    load

from chia_blockchain.chia.util.ints import uint32
from chia_blockchain.chia.util.bech32m import encode_puzzle_hash,\
    decode_puzzle_hash
from chia_blockchain.chia.util.keychain import Keychain
from chia_blockchain.chia.consensus.coinbase import create_puzzlehash_for_pk
from chia_blockchain.chia.wallet.derive_keys import master_sk_to_wallet_sk

parser = argparse.ArgumentParser(description='WILLOW-chia-forks-offline-wallet-balance')
parser.add_argument('-m','--mnemonic', help='The mnemonic used to create a private key. Use \'default\''
                                            ' to use the default mnemonic registered in the system\'s keychain.', required=False)
parser.add_argument('-d','--db_path', help='The path to the db where the balance will be queried.', required=False)
parser.add_argument('-p','--prefix', help='The prefix of the coin used to generate the addresses', required=True if __name__ == '__main__' else False, default='xch')
arguments = vars(parser.parse_args())


class willow():
    def __init__(self,
                 disable_print = False):

        self.disable_print = disable_print
        self.prefix = arguments['prefix']
        self.mnemonic = arguments['mnemonic']
        self.number_of_ph_to_search = 500

        if 'mnemonic' not in arguments.keys() and 'db_path' not in arguments.keys():
            exit('ERROR: Either the mnemonic needs to be provided (to create the json with all addresses) or the db path (to check the wallet balance) !')
        if 'mnemonic' in arguments.keys() and 'db_path' in arguments.keys():
            exit('ERROR: Either the mnemonic needs to be provided (to create the json with all addresses) or the db path (to check the wallet balance) !')

    def run(self):
        if 'mnemonic' in arguments.keys(): return self.create_addresses()
        if 'db_path' in arguments.keys(): return self. get_wallet_balance()

    def create_addresses(self):
        keychain: Keychain = Keychain()
        if self.mnemonic == 'default':
            all_sks = [(keychain.get_all_private_keys()[0][0], None)] # from hot wallet
        else:
            all_sks = [(keychain.return_private_key_from_mnemonic(mnemonic=self.mnemonic), None)]

        self.all_addresses = []

        for i in range(self.number_of_ph_to_search):
            for sk, _ in all_sks:
                self.all_addresses.append(
                    encode_puzzle_hash(create_puzzlehash_for_pk(master_sk_to_wallet_sk(sk, uint32(i)).get_g1()), self.prefix)
                )
        with open('first_{}_addresses_{}.json', 'w') as json_out_handle:
            dump(self.all_addresses, json_out_handle, indent=2)

        return self.all_addresses

    def get_wallet_balance(self):

        db_filepath = "C:\\Users\\g4m3rx\\.hddcoin\\mainnet\\db\\blockchain_v1_mainnet.sqlite"
        conn = connect(db_filepath)
        dbcursor = conn.cursor()

        total_coin_balance = 0
        total_coin_spent = 0

        required_filename = 'first_{}_addresses_{}.json'.format(self.number_of_ph_to_search,
                                                                  self.prefix)
        if not os_path.isfile(required_filename):
            exit('ERROR: {} missing. Run willow and provide the mnemonic to create the json with all the addresses.'.format(required_filename))
        else:
            with open(required_filename, 'r') as json_in_handle:
                self.all_addresses = load(json_in_handle)

        for wallet_addr in self.all_addresses:

            coin_balance = 0
            coin_spent = 0

            puzzle_hash_bytes = decode_puzzle_hash(wallet_addr)
            puzzle_hash = puzzle_hash_bytes.hex()

            dbcursor.execute("SELECT * FROM coin_record WHERE puzzle_hash=?", (puzzle_hash,))
            rows = dbcursor.fetchall()

            for row in rows:

                xch_raw=int.from_bytes(row[7], 'big')
                xch=xch_raw/1000000000000
                is_coin_spent = row[3]
                if is_coin_spent:
                    coin_spent = xch + coin_spent
                else:
                    coin_balance = xch + coin_balance

            if not self.disable_print:
                print('{} | available: {} | spent: {}'.format(wallet_addr,
                                           coin_balance,
                                           coin_spent))

        if not self.disable_print:
            print('TOTAL| available: {} | spent: {}'.format(total_coin_balance,
                                                            total_coin_spent))

        return {'total_coin_balance': total_coin_balance,
                'total_coin_spent': total_coin_spent,
                'coin': self.prefix}

if __name__ == '__main__':
    do = willow()
    do.run()