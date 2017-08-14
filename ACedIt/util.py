import sys
import json
import re
import os
try:
    from bs4 import BeautifulSoup as bs
    import requests as rq
    import grequests as grq
    from argparse import ArgumentParser
except:
    err = """
    You haven't installed the required dependencies.
    Run 'python setup.py install' to install the dependencies.
    """
    print err
    sys.exit(0)


class Utilities:

    cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'ACedIt')
    colors = {
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'ENDC': '\033[0m',
        'BOLD': '\033[1m',
    }

    @staticmethod
    def parse_flags():
        """
        Utility function to parse command line flags
        """

        parser = ArgumentParser()

        parser.add_argument('-s', '--site',
                            dest='site',
                            help='The competitive programming platform, e.g. codeforces, codechef etc')

        parser.add_argument('-c', '--contest',
                            dest='contest',
                            help='The name of the contest, e.g. JUNE17, LTIME49, COOK83 etc')

        parser.add_argument('-p', '--problem',
                            dest='problem',
                            help='The problem code, e.g. OAK, PRMQ etc')

        parser.add_argument('-f', '--force',
                            dest='force',
                            action='store_true',
                            help='Force download the test cases, even if they are cached')

        parser.add_argument('--run',
                            dest='source_file',
                            help='Name of source file to be run')

        parser.set_defaults(force=False)

        args = parser.parse_args()

        flags = {}

        if args.site is None:
            import json
            default_site = None
            try:
                with open(os.path.join(Utilities.cache_dir, 'constants.json'), 'r') as f:
                    data = f.read()
                data = json.loads(data)
                default_site = data.get('default_site', None)
            except:
                pass

            flags['site'] = default_site
        else:
            flags['site'] = args.site

        flags['contest'] = args.contest
        flags['problem'] = args.problem
        flags['force'] = args.force
        flags['site'] = flags['site'].lower()
        flags['source'] = args.source_file

        return flags

    @staticmethod
    def create_workdir_structure(site, contest):
        """
        Method to create the working directory structure
        """
        try:
            with open(os.path.join(Utilities.cache_dir, 'constants.json'), 'r') as f:
                data = f.read()
            data = json.loads(data)
        except:
            pass

        workdir = data.get('workdir', None)

        if not os.path.isdir(os.path.join(workdir, site, contest)):
            os.makedirs(os.path.join(workdir, site, contest))

    @staticmethod
    def check_cache(site, contest, problem):
        """
        Method to check if the test cases already exist in cache
        If not, create the directory structure to store test cases
        """

        Utilities.create_workdir_structure(site, contest)

        if problem is None:
            if not os.path.isdir(os.path.join(Utilities.cache_dir, site, contest)):
                os.makedirs(os.path.join(Utilities.cache_dir, site,
                                         contest))
            return False

        if os.path.isdir(os.path.join(Utilities.cache_dir, site, contest, problem)):
            return True
        else:
            os.makedirs(os.path.join(Utilities.cache_dir, site,
                                     contest, problem))
            return False

    @staticmethod
    def store_files(site, contest, problem, inputs, outputs):
        """
        Method to store the test cases in files
        """
        for i, inp in enumerate(inputs):
            filename = os.path.join(
                Utilities.cache_dir, site, contest, problem, 'Input' + str(i))
            with open(filename, 'w') as handler:
                handler.write(inp)

        for i, out in enumerate(outputs):
            filename = os.path.join(
                Utilities.cache_dir, site, contest, problem, 'Output' + str(i))
            with open(filename, 'w') as handler:
                handler.write(out)

    @staticmethod
    def download_problem_testcases(args):
        """
        Download test cases for a given problem
        """
        if args['site'] == 'codeforces':
            platform = Codeforces(args)
        elif args['site'] == 'codechef':
            platform = Codechef(args)
        elif args['site'] == 'spoj':
            platform = Spoj(args)
        else:
            platform = Hackerrank(args)

        is_in_cache = Utilities.check_cache(
            platform.site, platform.contest, platform.problem)

        if not args['force'] and is_in_cache:
            print 'Test cases found in cache...'
            sys.exit(0)

        platform.scrape_problem()

    @staticmethod
    def download_contest_testcases(args):
        """
        Download test cases for all problems in a given contest
        """
        if args['site'] == 'codeforces':
            platform = Codeforces(args)
        elif args['site'] == 'codechef':
            platform = Codechef(args)
        elif args['site'] == 'hackerrank':
            platform = Hackerrank(args)

        Utilities.check_cache(
            platform.site, platform.contest, platform.problem)

        platform.scrape_contest()

    @staticmethod
    def input_file_to_string(path, num_cases):
        """
        Method to return sample inputs as a list
        """
        inputs = []

        for i in xrange(num_cases):
            with open(os.path.join(path, 'Input' + str(i)), 'r') as fh:
                inputs += [fh.read()]

        return inputs

    @staticmethod
    def cleanup(num_cases):
        """
        Method to clean up temporarily created files
        """
        for i in xrange(num_cases):
            if os.path.isfile('temp_output' + str(i)):
                os.remove('temp_output' + str(i))

    @staticmethod
    def handle_kbd_interrupt(args):
        """
        Method to handle keyboard interrupt
        """
        from shutil import rmtree
        print 'Interrupted manually. Cleaning up...'

        if args['problem'] is not None:
            path = os.path.join(Utilities.cache_dir, args['site'], args[
                                'contest'], args['problem'])
            if os.path.isdir(path):
                rmtree(path)
        else:
            path = os.path.join(Utilities.cache_dir, args[
                                'site'], args['contest'])
            if os.path.isdir(path):
                rmtree(path)

        print 'Done. Exiting gracefully.'

    @staticmethod
    def run_solution(problem):
        """
        Method to run and test the user's solution against sample cases
        """
        extension = problem.split('.')[-1]
        problem = problem.split('.')[0]
        problem_path = os.path.join(os.getcwd(), problem)

        if not os.path.isfile(problem_path + '.' + extension):
            print 'ERROR : No such file'
            sys.exit(0)

        testcases_path = os.path.join(
            Utilities.cache_dir, *problem_path.split('/')[-3:])

        if os.path.isdir(testcases_path):
            num_cases = len(os.listdir(testcases_path)) / 2
            results, expected_outputs, user_outputs = [], [], []

            if extension == 'py':

                for i in xrange(num_cases):
                    status = os.system('cat ' + os.path.join(testcases_path, 'Input' + str(
                        i)) + ' | timeout 3s python ' + problem + '.py > temp_output' + str(i))
                    if status == 124:
                        # Time Limit Exceeded
                        results += [Utilities.colors['BOLD'] +
                                    Utilities.colors['YELLOW'] + 'TLE' + Utilities.colors['ENDC']]

                    elif status == 0:

                        with open('temp_output' + str(i), 'r') as temp_handler, open(os.path.join(testcases_path, 'Output' + str(i)), 'r') as out_handler:
                            expected_output = out_handler.read().strip().split('\n')
                            user_output = temp_handler.read().strip().split('\n')

                            expected_output = '\n'.join(
                                [line.strip() for line in expected_output])
                            user_output = '\n'.join(
                                [line.strip() for line in user_output])

                            expected_outputs += [expected_output]
                            user_outputs += [user_output]

                        if expected_output == user_output:
                            # All Correct
                            results += [Utilities.colors['BOLD'] + Utilities.colors[
                                'GREEN'] + 'AC' + Utilities.colors['ENDC']]
                        else:
                            # Wrong Answer
                            results += [Utilities.colors['BOLD'] +
                                        Utilities.colors['RED'] + 'WA' + Utilities.colors['ENDC']]

                    else:
                        # Runtime Error
                        results += [Utilities.colors['BOLD'] +
                                    Utilities.colors['RED'] + 'RTE' + Utilities.colors['ENDC']]

            elif extension == 'cpp' or extension == 'c':

                compiler = {'c': 'gcc', 'cpp': 'g++'}[extension]
                compile_status = os.system(
                    compiler + ' ' + problem_path + '.cpp')

                if compile_status == 0:
                    for i in xrange(num_cases):
                        status = os.system('timeout 2s ./a.out < ' + os.path.join(
                            testcases_path, 'Input' + str(i)) + ' > temp_output' + str(i))
                        if status == 124:
                            # Time Limit Exceeded
                            results += [Utilities.colors['BOLD'] + Utilities.colors[
                                'YELLOW'] + 'TLE' + Utilities.colors['ENDC']]

                        elif status == 0:

                            with open('temp_output' + str(i), 'r') as temp_handler, open(os.path.join(testcases_path, 'Output' + str(i)), 'r') as out_handler:
                                expected_output = out_handler.read().strip().split('\n')
                                user_output = temp_handler.read().strip().split('\n')

                                expected_output = '\n'.join(
                                    [line.strip() for line in expected_output])
                                user_output = '\n'.join(
                                    [line.strip() for line in user_output])

                                expected_outputs += [expected_output]
                                user_outputs += [user_output]

                            if expected_output == user_output:
                                # All Correct
                                results += [Utilities.colors['BOLD'] + Utilities.colors[
                                    'GREEN'] + 'AC' + Utilities.colors['ENDC']]
                            else:
                                # Wrong Answer
                                results += [Utilities.colors['BOLD'] + Utilities.colors[
                                    'RED'] + 'WA' + Utilities.colors['ENDC']]

                        else:
                            # Runtime Error
                            results += [Utilities.colors['BOLD'] +
                                        Utilities.colors['RED'] + 'RTE' + Utilities.colors['ENDC']]
                else:
                    # Compilation error occurred
                    message = Utilities.colors['BOLD'] + Utilities.colors[
                        'RED'] + 'Compilation error. Not run against test cases' + Utilities.colors['ENDC'] + '.'
                    print message
                    sys.exit(0)

            else:
                print 'Supports only C++ and Python as of now. Support for Java coming soon.'
                sys.exit(0)

            from terminaltables import AsciiTable
            table_data = [['Serial No', 'Input',
                           'Expected Output', 'Your Output', 'Result']]

            inputs = Utilities.input_file_to_string(testcases_path, num_cases)

            for i in xrange(num_cases):

                row = [
                    i + 1,
                    inputs[i],
                    expected_outputs[i],
                    user_outputs[i] if any(sub in results[i]
                                           for sub in ['AC', 'WA']) else 'N/A',
                    results[i]
                ]

                table_data.append(row)

            table = AsciiTable(table_data)

            print table.table

            # Clean up temporary files
            Utilities.cleanup(num_cases)

        else:
            print 'Test cases not found locally...'
            args = {
                'site': testcases_path.split('/')[-3],
                'contest': testcases_path.split('/')[-2],
                'problem': testcases_path.split('/')[-1],
                'force': True
            }
            Utilities.download_problem_testcases(args)

            print 'Done. Running your solution against sample cases...'
            Utilities.run_solution(problem + '.' + extension)

    @staticmethod
    def get_html(url):
        """
        Utility function get the html content of an url
        """
        try:
            r = rq.get(url)
        except Exception as e:
            print 'Please check your internet connection and try again.'
            sys.exit(0)
        return r


class Codeforces:
    """
    Class to handle downloading of test cases from Codeforces
    """

    def __init__(self, args):
        self.site = args['site']
        self.contest = args['contest']
        self.problem = args['problem']
        self.force_download = args['force']

    def parse_html(self, req):
        """
        Method to parse the html and get test cases
        from a codeforces problem
        """
        soup = bs(req.text, 'html.parser')

        inputs = soup.findAll('div', {'class': 'input'})
        outputs = soup.findAll('div', {'class': 'output'})

        repls = ('<br>', '\n'), ('<br/>', '\n'), ('</br>', '')

        formatted_inputs, formatted_outputs = [], []

        for inp in inputs:
            pre = inp.find('pre').decode_contents()
            pre = reduce(lambda a, kv: a.replace(*kv), repls, pre)
            pre = re.sub('<[^<]+?>', '', pre)
            formatted_inputs += [pre]

        for out in outputs:
            pre = out.find('pre').decode_contents()
            pre = reduce(lambda a, kv: a.replace(*kv), repls, pre)
            pre = re.sub('<[^<]+?>', '', pre)
            formatted_outputs += [pre]

        # print 'Inputs', formatted_inputs
        # print 'Outputs', formatted_outputs

        return formatted_inputs, formatted_outputs

    def get_problem_links(self, req):
        """
        Method to get the links for the problems
        in a given codeforces contest
        """
        soup = bs(req.text, 'html.parser')

        table = soup.find('table', {'class': 'problems'})
        links = ['http://codeforces.com' +
                 td.find('a')['href'] for td in table.findAll('td', {'class': 'id'})]

        return links

    def scrape_problem(self):
        """
        Method to scrape a single problem from codeforces
        """
        print 'Fetching problem ' + self.contest + '-' + self.problem + ' from Codeforces...'
        url = 'http://codeforces.com/contest/' + \
            self.contest + '/problem/' + self.problem
        req = Utilities.get_html(url)
        inputs, outputs = self.parse_html(req)
        Utilities.store_files(self.site, self.contest,
                              self.problem, inputs, outputs)
        print 'Done.'

    def scrape_contest(self):
        """
        Method to scrape all problems from a given codeforces contest
        """
        print 'Checking problems available for contest ' + self.contest + '...'
        url = 'http://codeforces.com/contest/' + self.contest
        req = Utilities.get_html(url)
        links = self.get_problem_links(req)

        print 'Found %d problems..' % (len(links))

        if not self.force_download:
            cached_problems = os.listdir(os.path.join(
                Utilities.cache_dir, self.site, self.contest))
            links = [link for link in links if link.split(
                '/')[-1] not in cached_problems]

        rs = (grq.get(link) for link in links)
        responses = grq.map(rs)

        for response in responses:
            if response is not None and response.status_code == 200:
                inputs, outputs = self.parse_html(response)
                self.problem = response.url.split('/')[-1]
                Utilities.check_cache(self.site, self.contest, self.problem)
                Utilities.store_files(
                    self.site, self.contest, self.problem, inputs, outputs)


class Codechef:
    """
    Class to handle downloading of test cases from Codechef
    """

    def __init__(self, args):
        self.site = args['site']
        self.contest = args['contest']
        self.problem = args['problem']
        self.force_download = args['force']

    def parse_html(self, req):
        """
        Method to parse the html and get test cases
        from a codechef problem
        """
        data = json.loads(req.text)
        soup = bs(data['body'], 'html.parser')

        test_cases = soup.findAll('pre')
        formatted_inputs, formatted_outputs = [], []

        input_list = [
            '<pre>(.|\n)*<b>Input:?</b>:?',
            '<b>Output:?</b>(.|\n)+</pre>'
        ]

        output_list = [
            '<pre>(.|\n)+<b>Output:?</b>:?',
            '</pre>'
        ]

        input_regex = re.compile('(%s)' % '|'.join(input_list))
        output_regex = re.compile('(%s)' % '|'.join(output_list))

        for case in test_cases:
            inp = input_regex.sub('', str(case))
            out = output_regex.sub('', str(case))

            inp = re.sub('<[^<]+?>', '', inp)
            out = re.sub('<[^<]+?>', '', out)

            formatted_inputs += [inp.strip()]
            formatted_outputs += [out.strip()]

        # print 'Inputs', formatted_inputs
        # print 'Outputs', formatted_outputs

        return formatted_inputs, formatted_outputs

    def get_problem_links(self, req):
        """
        Method to get the links for the problems
        in a given codechef contest
        """
        soup = bs(req.text, 'html.parser')

        table = soup.find('table', {'class': 'dataTable'})
        links = [div.find('a')['href']
                 for div in table.findAll('div', {'class': 'problemname'})]
        links = ['https://codechef.com/api/contests/' + self.contest +
                 '/problems/' + link.split('/')[-1] for link in links]

        return links

    def scrape_problem(self):
        """
        Method to scrape a single problem from codechef
        """
        print 'Fetching problem ' + self.contest + '-' + self.problem + ' from Codechef...'
        url = 'https://codechef.com/api/contests/' + \
            self.contest + '/problems/' + self.problem
        req = Utilities.get_html(url)
        inputs, outputs = self.parse_html(req)
        Utilities.store_files(self.site, self.contest,
                              self.problem, inputs, outputs)
        print 'Done.'

    def scrape_contest(self):
        """
        Method to scrape all problems from a given codechef contest
        """
        print 'Checking problems available for contest ' + self.contest + '...'
        url = 'https://codechef.com/' + self.contest
        req = Utilities.get_html(url)
        links = self.get_problem_links(req)

        print 'Found %d problems..' % (len(links))

        if not self.force_download:
            cached_problems = os.listdir(os.path.join(
                Utilities.cache_dir, self.site, self.contest))
            links = [link for link in links if link.split(
                '/')[-1] not in cached_problems]

        # rs = (grq.get(link) for link in links)
        # responses = grq.map(rs)

        responses = []
        for link in links:
            responses += [rq.get(link)]

        for response in responses:
            if response is not None and response.status_code == 200:
                inputs, outputs = self.parse_html(response)
                self.problem = response.url.split('/')[-1]
                Utilities.check_cache(self.site, self.contest, self.problem)
                Utilities.store_files(
                    self.site, self.contest, self.problem, inputs, outputs)


class Spoj:
    """
    Class to handle downloading of test cases from Spoj
    """

    def __init__(self, args):
        self.site = args['site']
        self.contest = args['contest']
        self.problem = args['problem']
        self.force_download = args['force']

    def parse_html(self, req):
        """
        Method to parse the html and get test cases
        from a spoj problem
        """
        soup = bs(req.text, 'html.parser')

        test_cases = soup.findAll('pre')
        formatted_inputs, formatted_outputs = [], []

        input_list = [
            '<pre>(.|\n|\r)*<b>Input:?</b>:?',
            '<b>Output:?</b>(.|\n|\r)*'
        ]

        output_list = [
            '<pre>(.|\n|\r)*<b>Output:?</b>:?',
            '</pre>'
        ]

        input_regex = re.compile('(%s)' % '|'.join(input_list))
        output_regex = re.compile('(%s)' % '|'.join(output_list))

        for case in test_cases:
            inp = input_regex.sub('', str(case))
            out = output_regex.sub('', str(case))

            inp = re.sub('<[^<]+?>', '', inp)
            out = re.sub('<[^<]+?>', '', out)

            formatted_inputs += [inp.strip()]
            formatted_outputs += [out.strip()]

        # print 'Inputs', formatted_inputs
        # print 'Outputs', formatted_outputs

        return formatted_inputs, formatted_outputs

    def scrape_problem(self):
        """
        Method to scrape a single problem from spoj
        """
        print 'Fetching problem ' + self.problem + ' from SPOJ...'
        url = 'http://spoj.com/problems/' + self.problem
        req = Utilities.get_html(url)
        inputs, outputs = self.parse_html(req)
        Utilities.store_files(self.site, self.contest,
                              self.problem, inputs, outputs)
        print 'Done.'


class Hackerrank:
    """
    Class to handle downloading of test cases from Hackerrank
    """

    def __init__(self, args):
        self.site = args['site']
        self.contest = args['contest']
        self.problem = '-'.join(args['problem'].split()
                                ).lower() if args['problem'] is not None else None
        self.force_download = args['force']

    def parse_html(self, req):
        """
        Method to parse the html and get test cases
        from a hackerrank problem
        """
        data = json.loads(req.text)
        soup = bs(data['model']['body_html'], 'html.parser')

        input_divs = soup.findAll('div', {'class': 'challenge_sample_input'})
        output_divs = soup.findAll('div', {'class': 'challenge_sample_output'})

        inputs = [input_div.find('pre') for input_div in input_divs]
        outputs = [output_div.find('pre') for output_div in output_divs]

        regex_list = [
            '<pre>(<code>)?',
            '(</code>)?</pre>'
        ]

        regex = re.compile('(%s)' % '|'.join(regex_list))

        formatted_inputs, formatted_outputs = [], []

        for inp in inputs:
            spans = inp.findAll('span')
            if len(spans) > 0:
                formatted_input = '\n'.join(
                    [span.decode_contents() for span in spans])
            else:
                formatted_input = regex.sub('', str(inp))

            formatted_inputs += [formatted_input.strip()]

        for out in outputs:
            spans = out.findAll('span')
            if len(spans) > 0:
                formatted_output = '\n'.join(
                    [span.decode_contents() for span in spans])
            else:
                formatted_output = regex.sub('', str(out))

            formatted_outputs += [formatted_output.strip()]

        # print 'Inputs', formatted_inputs
        # print 'Outputs', formatted_outputs

        return formatted_inputs, formatted_outputs

    def get_problem_links(self, req):
        """
        Method to get the links for the problems
        in a given hackerrank contest
        """
        data = json.loads(req.text)
        data = data['models']
        links = ['https://www.hackerrank.com/rest/contests/' + self.contest +
                 '/challenges/' + problem['slug'] for problem in data]

        return links

    def scrape_problem(self):
        """
        Method to scrape a single problem from hackerrank
        """
        print 'Fetching problem ' + self.contest + '-' + self.problem + ' from Hackerrank...'
        url = 'https://www.hackerrank.com/rest/contests/' + \
            self.contest + '/challenges/' + self.problem
        req = Utilities.get_html(url)
        inputs, outputs = self.parse_html(req)
        Utilities.store_files(self.site, self.contest,
                              self.problem, inputs, outputs)
        print 'Done.'

    def scrape_contest(self):
        """
        Method to scrape all problems from a given hackerrank contest
        """
        print 'Checking problems available for contest ' + self.contest + '...'
        url = 'https://www.hackerrank.com/rest/contests/' + self.contest + '/challenges'
        req = Utilities.get_html(url)
        links = self.get_problem_links(req)

        print 'Found %d problems..' % (len(links))

        if not self.force_download:
            cached_problems = os.listdir(os.path.join(
                Utilities.cache_dir, self.site, self.contest))
            links = [link for link in links if link.split(
                '/')[-1] not in cached_problems]

        rs = (grq.get(link) for link in links)
        responses = grq.map(rs)

        for response in responses:
            if response is not None and response.status_code == 200:
                inputs, outputs = self.parse_html(response)
                self.problem = response.url.split('/')[-1]
                Utilities.check_cache(self.site, self.contest, self.problem)
                Utilities.store_files(
                    self.site, self.contest, self.problem, inputs, outputs)
