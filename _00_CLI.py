from argparse import ArgumentParser
from _00_WILLOW_base import configure_logger_and_queue,\
    config_handler
from _00_back_end import WILLOW_back_end
import os

class WILLOWcli(configure_logger_and_queue,
                config_handler):

    def __init__(self):
        super(WILLOWcli, self).__init__()


    def return_configured_coins(self):
        return [entry[0] for entry in self.config['assets'].items()]

    def check_valid_coin(self,
                         coin):
        if coin not in [entry[0] for entry in self.config['assets'].items()]:
            return False
        return True

parser = ArgumentParser(description='CLI: WILLOW-chia-forks-offline-wallet-balance |'
                                    ' ' + open(os.path.join(os.path.dirname(__file__),'version.txt'), 'r').read())

parser.add_argument('-c',
                    '--coin',
                    type=str,
                    help='Coin to be processed, Can be one of the following: {}'.format('|'.join(coin for coin in WILLOWcli().return_configured_coins())))

parser.add_argument('-m',
                    '--mnemonic',
                    nargs='*',
                    help='The mnemonic to be used to generate the addresses. (Optional)',
                    default = None)

parser.add_argument('-a',
                    '--addresses',
                    nargs='*',
                    help='The addresses to check. (Optional)',
                    default=None)

parser.add_argument('-n',
                    '--numberAddresses',
                    type=int,
                    help='How many addresses to create ? Default 500.',
                    default=500)

parser.add_argument('--cats', dest='cats_only', action='store_true')
parser.add_argument('--no-cats', dest='cats_only', action='store_false')
parser.set_defaults(cats_only=False)

parser.add_argument('--just_addresses', dest='just_addresses', action='store_true')
parser.set_defaults(just_addresses=False)

if __name__ == '__main__':

    args = parser.parse_args()

    class mixer(WILLOWcli,
                WILLOW_back_end):
        def __init__(self):
            super(mixer, self).__init__()

    WILLOWobj = mixer()
    if not args.just_addresses:
        WILLOWobj.exec_full_cycle(mnemonic=' '.join(args.mnemonic),
                                  prefix=args.coin.lower(),
                                  asset=args.coin,
                                  cats_only=args.cats_only,
                                  nr_of_addresses=args.numberAddresses,
                                  custom_addresses=args.addresses)
    else:
        print(str(WILLOWobj.return_addresses(mnemonic=' '.join(args.mnemonic),
                                             prefix=args.coin.lower(),
                                             asset=args.coin,
                                             nr_of_addresses=args.numberAddresses)))