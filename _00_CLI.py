from argparse import ArgumentParser
from _00_base import configure_logger_and_queue,\
    config_handler
from _00_back_end import select_backend
import os,\
    sys
from logging import getLogger

class WILLOWcli(configure_logger_and_queue,
                config_handler):

    def __init__(self):
        super(WILLOWcli, self).__init__()


    def return_configured_coins(self):
        return [entry[0] for entry in self.config.items()]

    def check_valid_coin(self,
                         coin):
        if coin not in [entry[0] for entry in self.config.items()]:
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

    class mixer(WILLOWcli,
                select_backend(coin=args.coin)):
        def __init__(self):
            super(mixer, self).__init__()

    WILLOWobj = mixer()

    if not WILLOWobj.check_valid_coin(coin=args.coin):
        sys.exit('Your coin is not in the config: {}'.format(args.coin))

    if not args.mnemonic and not args.addresses:
        sys.exit('At least a mnemonic or some addresses must be provided !')

    if args.mnemonic and args.addresses:
        sys.exit('No mnemonic and no addresses were provided !')

    call_params = {'coin': args.coin}

    if args.mnemonic:
        call_params.update({'addresses': WILLOWobj.return_addresses(mnemonic=args.mnemonic,
                                                                   prefix=args.coin.lower(),
                                                                   nr_of_addresses=args.numberAddresses)})
    if args.addresses:
        call_params.update({'addresses': args.addresses})

    message_payload = WILLOWobj.return_total_balance(**call_params)

    if not args.verbose:
        print('$${}$$'.format(str(message_payload)))
    else:
        log = getLogger()
        for message in message_payload['message_payload']:
            # getattr seems to fail here ...
            if message[0] == 'info':
                log.info(message[1])
            elif message[0] == 'error':
                log.error(message[1])
            else:
                log.info(message[1])