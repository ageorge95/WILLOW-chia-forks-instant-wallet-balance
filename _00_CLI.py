from argparse import ArgumentParser
from _00_base import configure_logger_and_queue
from _00_back_end import WILLOW_back_end
import os

class WILLOWcli(configure_logger_and_queue,
                WILLOW_back_end):

    def __init__(self):
        super(WILLOWcli, self).__init__()

    def return_configured_coins(self):
        return [entry[0] for entry in self.config.items()]

    def check_valid_coin(self,
                         coin):
        if coin not in [entry[0] for entry in self.config.items()]:
            return False
        return True

parser = ArgumentParser(description='WILLOW CLI interface')

parser.add_argument('-c',
                    '--coin',
                    type=str,
                    help='Coin to be processed, Can be one of the following: {}'.format('|'.join(coin for coin in WILLOWcli().return_configured_coins())))

parser.add_argument('-m',
                    '--mnemonic',
                    type=str,
                    help='The mnemonic to be used to generate the addresses. Optional.',
                    default = None)

parser.add_argument('-a',
                    '--addresses',
                    nargs='+',
                    help='The addresses to check. Optional.',
                    default=None)

parser.add_argument('-n',
                    '--numberAddresses',
                    type=int,
                    help='How many addresses to create ? Default 500.',
                    default=500)

parser.add_argument('--verbose', dest='verbose', action='store_true')
parser.add_argument('--no-verbose', dest='verbose', action='store_false')
parser.set_defaults(verbose=True)

if __name__ == '__main__':

    os.system("color") # enable color in the console

    args = parser.parse_args()

    WILLOWobj = WILLOWcli()

    if not WILLOWobj.check_valid_coin(coin=args.coin):
        exit('Your coin is not in the config: {}'.format(args.coin))

    if not args.mnemonic and not args.addresses:
        exit('At least a mnemonic or some addresses must be provided !')

    if args.mnemonic and args.addresses:
        exit('No mnemonic and no addresses were provided !')

    WILLOWobj.return_total_balance(addresses=WILLOWobj.return_addresses(mnemonic=args.mnemonic,
                                                                       prefix=args.coin.lower(),
                                                                       nr_of_addresses=args.numberAddresses,
                                                                       verbose=args.verbose),
                                   coin=args.coin,
                                   verbose=args.verbose)