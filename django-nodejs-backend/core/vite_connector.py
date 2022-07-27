"""
Manage VITE Blockchain API via @vite.js NODE.JS package
https://github.com/vitelabs/vite.js
https://docs.vite.org/vite-docs/vite.js/
"""
import subprocess
import time

SCRIPT_PATH = "static/src/js/api_handler.js"


class ViteConnector:
    """Connect to VITE node and manage VITE blockchain API calls via NODE.JS scripts
    Possible status: running, finished, failed
    :param logs_from_nodejs:  True
    :param balance_response: dict = {}
    :param update_response: dict = {}
    :param send_response: dict = {}
    :param status:  'running'
    :param node_url:  node_url
    :param logger:  logger
    :param method:  method
    """
    script = SCRIPT_PATH

    def __init__(self, logger: object, method: str = 'http', node_url: str = None):
        self.logs_from_nodejs = True
        self.balance_response: dict = {}
        self.update_response: dict = {}
        self.send_response: dict = {}
        self.node_url = node_url
        self.last_log: str = ''
        self.logger = logger
        self.method = method
        self.status = 'running'

    def _run_command(self, command) -> dict:
        """
        Run NodeJS scripts with subprocess.Popen(), parse stdout
        and return dictionary with script payload.
        :param command: Full NodeJS command as list
        :return: dict,
        """
        logs_list = []

        # Run the command as subprocess and read output
        process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)

        # While process is running collect and filter logs
        while True:
            output = process.stdout.readline()

            if output == '' and process.poll() is not None:
                # Process finished
                break
            if output.strip().startswith('>>'):
                # Filter logs from NodeJS to self.logger
                line = output.strip().replace('>>', 'node.js >>')
                if self.logs_from_nodejs and self.last_log != line: self.logger.info(line)
                self.last_log = line
            elif output and not output.startswith((' >>', '>>')):
                # Append parts of dictionary for return
                logs_list.append(output)

        # If process finished
        if not process.poll():
            try:
                # Serialize stdout output and return dict
                logs_list = [line.replace('null', 'None') for line in logs_list]
                logs_list = [line.replace('true', 'True') for line in logs_list]
                logs_list = [line.replace('false', 'False') for line in logs_list]
                logs_json = ''.join([line.replace('\n', '') for line in logs_list])
                logs_dict = eval(logs_json)
                return logs_dict

            except Exception as e:
                return {'error': 1, 'msg': e, 'data': None}

    def _balance(self, **kwargs) -> dict:
        try_counter = 10
        args = ('address', 'mnemonics', 'address_id')

        if args[0] in kwargs:
            command = ['node', self.script, 'balance', '-a', kwargs['address']]

        elif all(arg in args[1:] for arg in kwargs):
            kwargs['address_id'] = str(kwargs['address_id'])
            command = ['node', self.script, 'balance', '-a', '0',
                       '-m', kwargs['mnemonics'], '-i', kwargs['address_id']]
        else:
            return {'error': 1, 'msg': f'missing args, any of {args}', 'data': None}

        response = self._run_command(command)

        while response['error'] and try_counter:
            try_counter -= 1

            if 'timeout' in response['msg']:
                self.logger.warning(f"{response['msg']} re-try balance ({try_counter} left)")
                self._run_command(command)
            else:
                return response

        if not try_counter:
            response = {'error': 1, 'msg': "too many getBalance fail attempts", 'data': None}

        return response

    def create_wallet(self):
        command = ['node', self.script, 'create']
        return self._run_command(command)

    def balance(self, **kwargs) -> dict:
        self.balance_response = self._balance(**kwargs)

        if self.balance_response['error']:
            self.status = 'failed'
        else:
            self.status = 'finished'

        self.logger.info(f"{self.status} |  {self.balance_response['msg']}")
        return self.balance_response

    def send(self, **kwargs) -> dict:
        try_counter = 3
        args = ('mnemonics', 'address_id', 'to_address', 'token_id', 'amount')

        # Get sender's last transaction ID, later will be
        # used to confirm that transaction was sent successfully.
        last_tx_id = self._get_last_tx_id(**kwargs)

        if all(arg in args for arg in kwargs):
            kwargs['address_id'] = str(kwargs['address_id'])
            kwargs['amount'] = str(kwargs['amount'])
            command = ['node', self.script, 'send',
                       '-m', kwargs['mnemonics'],
                       '-i', kwargs['address_id'],
                       '-d', kwargs['to_address'],
                       '-t', kwargs['token_id'],
                       '-a', kwargs['amount']]

            self.send_response = self._run_command(command)

            while self.send_response['error'] and try_counter:
                if 'timeout' in self.send_response['msg'].lower():
                    try_counter -= 1
                    time.sleep(1)
                    current_tx_id = self._get_last_tx_id(**kwargs)

                    while not current_tx_id:
                        self.logger.critical(f"problem with getting balance, re-try...")
                        current_tx_id = self._get_last_tx_id(**kwargs)

                    if current_tx_id == last_tx_id:
                        self.logger.warning(f"{self.send_response['msg']}, re-try send ({try_counter} left)..")
                        time.sleep(1)
                        self.send_response = self._run_command(command)

                    else:
                        self.logger.info(f"New TX last ID [{current_tx_id}], finishing process..")
                        break
                else:
                    break

            if try_counter < 1:
                self.send_response = {'error': 1, 'msg': "Too many failed attempts", 'data': None}
                self.status = 'failed'
            elif self.send_response['error']:
                self.status = 'failed'
            else:
                self.status = 'finished'

            self.logger.info(f"{self.status} |  {self.send_response['msg']}")
            return self.send_response

    def update(self, **kwargs) -> dict:
        try_counter = 5
        args = ('mnemonics', 'address_id')

        if all(arg in args for arg in kwargs):
            kwargs['address_id'] = str(kwargs['address_id'])
            command = ['node', self.script, 'update', '-m', kwargs['mnemonics'], '-i', kwargs['address_id']]
            self.update_response = self._run_command(command)

            while self.update_response['error'] and try_counter:
                try_counter -= 1

                if 'timeout' in self.update_response['msg'].lower():
                    self.logger.info(f"{self.update_response['msg']}, re-try update ({try_counter} left)")
                    self._run_command(command)
                elif 'no pending' in self.update_response['msg'].lower():
                    self.update_response = {'error': 0, 'msg': "No pending transactions", 'data': None}
                    break
                else:
                    break

            if not try_counter:
                self.update_response = {'error': 1, 'msg': "Too many failed attempts", 'data': None}
                self.status = 'failed'

            elif self.update_response['error']:
                self.status = 'failed'

            else:
                self.status = 'finished'

        self.logger.info(f"{self.status} |  {self.update_response['msg']}")
        return self.update_response

    def _get_last_tx_id(self, **kwargs) -> int:
        kwargs = {'mnemonics': kwargs['mnemonics'],
                  'address_id': kwargs['address_id']}
        balance = self._balance(**kwargs)

        if not balance['error']:
            try:
                return balance['data']['balance']['blockCount']
            except Exception as e:
                self.logger.warning(f"_get_last_tx_id(): {e}")
        return 0