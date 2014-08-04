import re
import string


class Template(object):
    def __init__(self):
        self.data = []
        self.code_ph = "<__MARK_CODE__>"
        self.return_str_var = "_mark_result_str"

    def parse(self, input_tpl):
        """Parse the template file"""
        #First Remove all comments
        input_tpl = re.sub(r"(?<![\\])~=.+", "", input_tpl)
        #Find all of the code blocks
        code_blocks = re.findall(r"((?<![\\])~%\s.+?(?<![\\])~%\send)", input_tpl, re.S)
        #Replace all of the code blocks and format the code to be ran
        for code in code_blocks:
            input_tpl = input_tpl.replace(code, self.code_ph, 1)
            self.format_code_line(code)
        return input_tpl

    def render(self, input_tpl, **params):
        """Put the template back together for use"""
        #Check if the input is a readable file, if not treat it as a string
        try:
            with open(input_tpl) as f:
                input_tpl = f.read()
        except FileNotFoundError:
            pass
        #Replace the parameter variables
        str_template = string.Template(input_tpl)
        input_tpl = str_template.safe_substitute(params)
        #Parse the file to extract template code
        input_tpl = self.parse(input_tpl)
        #Execute the template code
        input_tpl = self.compile_insert(input_tpl)
        #Remove template escapes
        input_tpl = re.sub(r"([\\])(~=|~!|~%|~py|{[a-zA-Z_][a-zA-Z0-9_]*})", "\g<2>", input_tpl)
        return input_tpl

    def compile_insert(self, input_tpl):
        """Execute the code extracted from the template"""
        d = {}
        for code in self.data:
            d[self.return_str_var] = ""
            exec(code, d)
            output = d[self.return_str_var]
            input_tpl = input_tpl.replace(self.code_ph, output, 1)
        return input_tpl

    def format_code_line(self, code_raw):
        """Change from template code to python code"""
        # remove ending line and strip the whitespace
        code_list = [x.strip() for x in re.sub("\s+~%\send\.*", "", code_raw).split('\n')]
        # format each code line
        block_count = 0
        formatted_code_list = []
        for line in code_list:
            if line != "":
                #if a code condition is found
                if line.startswith('~%'):
                    line = line.replace('~%', '').strip()+':'
                    if line.startswith('elif') or line.startswith('else'):
                        line = "\n"+line
                    block_count = 0
                #if should be ignored
                elif line.startswith('~!'):
                    line = re.sub('~!\s', "", line)
                    if block_count == 0:
                        line = self.return_str_var+"+="+line
                    block_count += 1
                #if a python statement
                elif line.startswith('~py'):
                    line = re.sub('~py\s', "", line)
                    line += ";"
                #if inside the code block
                else:
                    #Check for a python variable
                    pyth_vars = re.findall(r"[^\\]{[a-zA-Z_][a-zA-Z0-9_]*}", line)
                    for var in pyth_vars:
                        var_key = var
                        var = re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", line)[0].strip()
                        line = line.replace(var_key, "'+str("+var+")+'", 1)
                    tag = re.findall(r"(\w+)\s", line)[0]
                    text = re.findall(r"\w+\s(.+)", line)[0]
                    line = "'<"+tag+">"+text+"</"+tag+">'"
                    if block_count == 0:
                        line = self.return_str_var+"+="+line
                    elif block_count > 0:
                        line = "+"+line
                    block_count += 1
                #Add the formatted line onto the code to execute
                formatted_code_list.append(line)
        exec_line = ''
        for x in formatted_code_list:
            exec_line += x
        self.data.append(exec_line)