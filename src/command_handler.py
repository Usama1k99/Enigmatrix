import os
import sys
import time
import ctypes
import psutil
import shlex
import utils
import key_utils
import encryptor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from command_configs import *
from cfg import *


def safe_eval(expr):
    """Evaluates a mathematical expression safely with arithmetic & bitwise operations."""
    tree = ast.parse(expr, mode='eval')  # Parse expression safely
    return eval_node(tree.body)  # Evaluate the parsed tree

def eval_node(node):
    """Recursively evaluates AST nodes."""
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](eval_node(node.left), eval_node(node.right))
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](eval_node(node.operand))
    raise ValueError("Invalid operation")

def command(name=None, aliases=None):
    """Decorator to register a command with optional aliases."""
    aliases = [] if not aliases else aliases
    def decorator(func):
        cmd_name = name if name else func.__name__
        aliases.append(cmd_name)
        aliases.append(func.__name__) if func.__name__ not in aliases else None
        for alias in aliases:
            if alias in COMMANDS.keys():
                raise ValueError(f"Command '{alias}' already exists.")
            COMMANDS[alias] = func
            COMMAND_ALIASES[alias] = cmd_name
        return func
    return decorator

def execute_command(input_text, app):
    """Parses user input and executes the corresponding function."""
    command, args, kwargs = parse_command(input_text)
    cmdl = command.lower()
    terminal = app.retro_terminal
    if terminal.awaiting_response:
        if cmdl.startswith("y") or cmdl.startswith("n"):
            if cmdl.startswith("y"):
                return terminal.exec_pending()
            else:
                return terminal.confirmed(False)
            return
        else:
            return terminal.type_text("Invalid Response.")
    try:
        result = safe_eval(input_text)
        if result is not None:
            return app.retro_terminal.type_text(result)
    except :
        pass
    # Handling commands which require full text
    if cmdl in ["echo", "print", "say"]:
        text = input_text[len(cmdl):].strip()
        return app.retro_terminal.type_text(text)
    if input_text.startswith("#"):
        return
    kwargs = utils.normalize_kwargs(kwargs)
    if cmdl in COMMANDS:
        app.retro_terminal.setReadOnly(True)
        COMMANDS[cmdl](app, *args, **kwargs)
        app.retro_terminal.setReadOnly(False)
    else:
        app.retro_terminal.type_text(f"Unknown command : \"{command}\"")

def parse_command(command: str):
    tokens = shlex.split(command.replace("\\", "\\\\"))
    if not tokens:
        return None, {}, []
    cmd = tokens[0]
    args = []
    kwargs = {}
    i = 1
    while i < len(tokens):
        if tokens[i].startswith("--"):
            key = tokens[i][2:]
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                kwargs[key] = tokens[i + 1]
                i += 1
            else:
                kwargs[key] = True
        else:
            args.append(tokens[i])
        i += 1
    return cmd, args, kwargs

# =========================== Commands =========================== #
@command(name="help", aliases=["h"])
def show_help(app, topic=None,*args,**kwargs):
    """Displays help information for commands and categories."""
    help_text = "Available command categories:\n"
    for category in COMMAND_CATEGORIES:
        help_text += f"> {category.capitalize()}\n"
    help_text += 'Use "help <category>" to list commands, or "help <command>" for command details.'
    # If no topic is given, show general help
    if not topic:
        return app.retro_terminal.type_text(help_text)
    # Resolve alias to actual command name
    _topic = topic
    if topic in COMMAND_ALIASES:
        topic = COMMAND_ALIASES[topic]
    # Check if topic is a command
    if topic in COMMAND_DESCRIPTIONS:
        return app.retro_terminal.type_text(f"{_topic}: {COMMAND_DESCRIPTIONS[topic]}")
    # Check if topic is a category
    if topic in COMMAND_CATEGORIES:
        commands = ""
        for cmd in COMMAND_CATEGORIES[topic]:
            commands += f"> {cmd}\n"
        return app.retro_terminal.type_text(f"{topic.capitalize()} commands:\n{commands}")
    return app.retro_terminal.type_text(help_text)


@command(name="encrypt",aliases=["enc"])
def encrypt_cmd(app,input_file=None,output_file=None,raw_key=None,rsa_key=None,*args,**kwargs):
    inp = input_file if input_file else None
    out = output_file if output_file else None
    key = raw_key if raw_key else None
    rsa = rsa_key if rsa_key else None
    # Overwriting or initializing from kwargs based on user input
    inp = kwargs.get("input") if "input" in kwargs.keys() else inp
    out = kwargs.get("output") if "output" in kwargs.keys() else out
    key = kwargs.get("key") if "key" in kwargs.keys() else key
    rsa = kwargs.get("rsa") if "rsa" in kwargs.keys() else rsa
    # Check if all the required values are provided or not
    if None in (inp,out,key):
        return show_help(app,'encrypt')
    # Normalizing paths
    cwd = app.retro_terminal.cwd
    rsa_dir = utils.load_config()['rsa_directory']
    inp = os.path.abspath(os.path.join(cwd,inp))
    out = os.path.abspath(os.path.join(cwd,out))

    # Checking if files exists
    out_dir = "\\".join(out.split("\\")[:-1])
    if not os.path.exists(inp):
        return app.retro_terminal.type_text(f"Error: No such file exists: \"{inp}\"")
    if not os.path.isdir(out_dir):
        return app.retro_terminal.type_text(f"Error: No such directory exists \"{out_dir}\"")
    if rsa:
        if not os.path.isdir(rsa_dir):
            return app.retro_terminal.type_text("Your RSA directory does not exists, please select RSA directory again.")
        rsa = os.path.abspath(os.path.join(rsa_dir, rsa))
        if not os.path.exists(rsa):
            return app.retro_terminal.type_text(f"Error: No such file exists: \"{rsa}\"")
    # Handling crucial conditions
    if inp == out:
        return app.retro_terminal.type_text("Error: Input and output file paths cannot be same")
    if len(key) < MIN_KEY_LEN:
        return app.retro_terminal.type_text(f"Error: Key length should be minimum of {MIN_KEY_LEN} characters.")

    rkey = key
    key = key.encode()
    file_size,_,lcs = utils.file_info(inp)
    readable_size = utils.readable_size(file_size)
    est_size = utils.readable_size(utils.estimate_encrypted_size(file_size))
    if rsa:
        if not key_utils.detect_rsa_key(rsa) == "public":
            return app.retro_terminal.type_text(f"Error: Selected RSA key is not public \"{rsa}\"")
        # RSA key is public. proceed for operation
        public_key = key_utils.load_rsa_key(rsa)
        cb_args = (inp,out,key,public_key)
        msg = f"Successfully Encrypted:\n \"{inp}\"\nSaved at:\n\"{out}\"\nUsing\n\"{rsa}\""
        app.retro_terminal.set_pending_state(encryptor.encrypt_file,cb_args,msg)
        return app.retro_terminal.type_text(f"Confirmation:\n"
                                            f"Input:\n\"{inp}\"\n"
                                            f"File size: {readable_size}\n"
                                            f"Estimated size after encryption: {est_size}\n"
                                            f"Output:\n\"{out}\"\n"
                                            f"Key:\n\"{rkey}\"\n"
                                            f"RSA key:\n\"{rsa}\"\n"
                                            f"Operation : Encrypt\n"
                                            f"Are you sure you want to continue with this operation? (y/n)")
    else:
        cb_args = (inp,out,key)
        msg = f"Successfully Encrypted:\n\"{inp}\"\nSaved at:\n\"{out}\""
        app.retro_terminal.set_pending_state(encryptor.encrypt_file,cb_args,msg)
        return app.retro_terminal.type_text(f"Confirmation:\n"
                                            f"Input:\n\"{inp}\"\n"
                                            f"File size: {readable_size}\n"
                                            f"Estimated size after encryption: {est_size}\n"
                                            f"Output:\n\"{out}\"\n"
                                            f"Operation : Encrypt\n"
                                            f"Are you sure you want to continue with this operation? (y/n)")


@command(name="decrypt",aliases=["dec"])
def decryp_cmd(app,input_file=None,output_file=None,raw_key=None,rsa_key=None,*args,**kwargs):

    inp = input_file if input_file else None
    out = output_file if output_file else None
    key = raw_key if raw_key else None
    rsa = rsa_key if rsa_key else None
    # Overwriting or initializing from kwargs based on user input
    inp = kwargs.get("input") if "input" in kwargs.keys() else inp
    out = kwargs.get("output") if "output" in kwargs.keys() else out
    key = kwargs.get("key") if "key" in kwargs.keys() else key
    rsa = kwargs.get("rsa") if "rsa" in kwargs.keys() else rsa
    # Check if all the required values are provided or not
    if None in (inp, out) or (not key and not rsa):
        return show_help(app,'decrypt')
    # Normalizing paths
    cwd = app.retro_terminal.cwd
    rsa_dir = utils.load_config()['rsa_directory']
    inp = os.path.abspath(os.path.join(cwd, inp))
    out = os.path.abspath(os.path.join(cwd, out))

    # Checking if files exists
    out_dir = "\\".join(out.split("\\")[:-1])
    if not os.path.exists(inp):
        return app.retro_terminal.type_text(f"Error: No such file exists: \"{inp}\"")
    if not os.path.isdir(out_dir):
        return app.retro_terminal.type_text(f"Error: No such directory exists \"{out_dir}\"")
    # Handling crucial conditions
    if inp == out:
        return app.retro_terminal.type_text("Error: Input and output file paths cannot be same")
    if not utils.check_encrypted(inp):
        return app.retro_terminal.type_text(f"Error: Selected file is not encrypted by this software, or file might be corrupted.\n"
                                            f"Choose a different file.")
    rsa_flag, rsa_enc_key, lcs = utils.read_file_header(inp)
    if rsa_flag:
        if not rsa:
            return app.retro_terminal.type_text("This file requires RSA private key to decrypt. please select the key file and try agian.")
        if not os.path.isdir(rsa_dir):
            return app.retro_terminal.type_text("Your RSA directory does not exists, please select RSA directory again.")
        rsa = os.path.abspath(os.path.join(rsa_dir, rsa))
        if not os.path.exists(rsa):
            return app.retro_terminal.type_text(f"Error: No such file exists: \"{rsa}\"")
        elif key_utils.detect_rsa_key(rsa) != "private":
            return app.retro_terminal.type_text(f"Error: Selected RSA key is not private \"{rsa}\"")
        # RSA key is private. proceed for operation
        private_key = key_utils.load_rsa_key(rsa)
        cb_args = (inp, out,None,private_key)
        msg = f"Successfully Decrypted:\n \"{inp}\"\nSaved at:\n\"{out}\"\nUsing\n\"{rsa}\""
        app.retro_terminal.set_pending_state(encryptor.decrypt_file, cb_args, msg)
        return app.retro_terminal.type_text(f"Confirmation:\n"
                                            f"Input:\n\"{inp}\"\n"
                                            f"Output:\n\"{out}\"\n"
                                            f"RSA key:\n\"{rsa}\"\n"
                                            f"Operation : Decrypt\n"
                                            f"Are you sure you want to continue with this operation? (y/n)")
    else:
        if not key:
            return app.retro_terminal.type_text(f"This file requires key for decryption. please try again and enter key using --key")
        rkey = key
        key = key.encode()
        cb_args = (inp, out, key)
        msg = f"Successfully Decrypted:\n\"{inp}\"\nSaved at:\n\"{out}\""
        app.retro_terminal.set_pending_state(encryptor.decrypt_file, cb_args, msg)
        return app.retro_terminal.type_text(f"Confirmation:\n"
                                            f"Input:\n\"{inp}\"\n"
                                            f"Output:\n\"{out}\"\n"
                                            f"Operation : Decrypt\n"
                                            f"Are you sure you want to continue with this operation? (y/n)")


@command(name="clear", aliases=["cls"])
def clear(app, *args, **kwargs):
    app.retro_terminal.add_ascii_art(welcome_msg=True,clear=True,speed=250)

@command(name="cwd",aliases=["getcwd","pwd"])
def get_cwd(app,*args,**kwargs):
    app.retro_terminal.type_text(f"Current Directory: \"{app.retro_terminal.cwd}\"")

@command(name="cd")
def change_cwd(app,path=None,*args,**kwargs):
    if not path:
        return app.retro_terminal.type_text("Usage: cd <path>")
    full_path = os.path.abspath(os.path.join(app.retro_terminal.cwd,path))
    if os.path.isdir(full_path):
        app.retro_terminal.cwd = full_path
        return app.retro_terminal.type_text(f"Changed directory to: \"{full_path}\"")
    else:
        return app.retro_terminal.type_text(f"Error: No such directory \"{path}\"")

@command(name="tree")
def tree_command(app, path=".", *args, **kwargs):
    """
    Displays a directory tree structure of the given path.
    Defaults to current working directory if no path is provided.
    """
    cwd = app.retro_terminal.cwd
    full_path = os.path.abspath(os.path.join(cwd, path))
    if not os.path.exists(full_path):
        return app.retro_terminal.type_text(f"Error: Path '{path}' does not exist.")
    tree_output = "\n".join(utils.generate_tree(full_path))
    app.retro_terminal.type_text(f"Showing tree for path: \"{full_path}\"")
    app.retro_terminal.type_text(f"{tree_output}")

@command(name="ascii-art", aliases=["ascii","art"])
def ascii_art(app, *args, **kwargs):
    clear_flag = False
    if args:
        if args[0].lower() == "clear":
            clear_flag = True
    if kwargs:
        if "clear" in kwargs.keys():
            clear_flag = True
    return app.retro_terminal.add_ascii_art(welcome_msg=clear_flag, clear=clear_flag, speed=220)

@command(name="mode",aliases=['m'])
def set_mode(app, *args, **kwargs):
    window_mode = None
    ui_mode = None
    if not (args or kwargs):
        return show_help(app,'mode')
    else:
        if args:
            temp_args = [x.lower() for x in args]
            if 'reset' in temp_args:
                app.retro_terminal.type_text("Swtiching window and UI mode to default.")
                app.showNormal()
                return app.gui_frame.show()
            if "terminal" in temp_args:
                ui_mode = "terminal"
            elif "gui" in temp_args or "ui" in temp_args:
                ui_mode = "gui"

            window_mode = "fullscreen" if "fullscreen" in temp_args else window_mode
            window_mode = "maximize" if "maximize" in temp_args else window_mode
            window_mode = "normal" if "normal" in temp_args else window_mode
            window_mode = "small" if "small" in temp_args else window_mode
        if kwargs:
            keys = [x.lower() for x in kwargs.keys()]
            if 'reset' in keys:
                app.retro_terminal.type_text("Swtiching window and UI mode to default.")
                app.showNormal()
                return app.gui_frame.show()
            ui_mode = "terminal" if "terminal" in keys else ui_mode
            if "ui" in keys:
                ui_mode = "gui"
            window_mode = "fullscreen" if "fullscreen" in keys else window_mode
            window_mode = "maximize" if "maximize" in keys else window_mode
            window_mode = "normal" if "normal" in keys else window_mode
            window_mode = "small" if "small" in keys else window_mode
        if not (window_mode or ui_mode):
            return show_help(app,'mode')
        else:
            if window_mode == "fullscreen":
                app.retro_terminal.type_text("Switching to fullscreen mode")
                app.showFullScreen()
            elif window_mode == "maximize":
                app.retro_terminal.type_text("Switching to maximized window mode")
                app.showMaximized()
            elif window_mode == "normal":
                app.retro_terminal.type_text("Switching to normal window mode")
                if app.windowState() == Qt.WindowState.WindowFullScreen:
                    app.showMaximized()
                app.setMinimumSize(*NORMAL_WINDOW_SIZE)
                app.resize(*NORMAL_WINDOW_SIZE)
                app.showNormal()
            elif window_mode == "small":
                app.retro_terminal.type_text("Switching to small window mode")
                if app.windowState() == Qt.WindowState.WindowFullScreen:
                    app.showMaximized()
                app.setMinimumSize(*SMALL_WINDOW_SIZE)
                app.resize(*SMALL_WINDOW_SIZE)
                app.showNormal()
            if ui_mode == "terminal":
                app.retro_terminal.type_text("Showing full terminal")
                return app.gui_frame.hide()
            elif ui_mode == "gui":
                app.retro_terminal.type_text("Showing GUI frame")
                app.gui_frame.show()

@command(name="rsa-key", aliases=["rsa"])
def rsa_key_handle(app, *args, **kwargs):
    if not kwargs:
        return show_help(app,'rsa-key')
    else:
        keys = [x.lower() for x in kwargs.keys()]
        if "generate" in keys:
            rsa_dir = utils.get_rsa_directory()
            if rsa_dir:
                rsa_name = kwargs.get("generate")
                if rsa_name and isinstance(rsa_name,str):
                    all_rsa_files = utils.get_rsa_files()
                    prv_rsa_files = [x for x in all_rsa_files if x.endswith("_private.pem")]
                    existing_keys = set([x.replace("_private.pem", "") for x in prv_rsa_files])
                    if rsa_name in existing_keys:
                        msg = f"Successfully generated RSA key pair with name \"{rsa_name}\" and overwritten the files."
                        app.retro_terminal.set_pending_state(key_utils.generate_rsa_keypair,(rsa_name,rsa_dir),msg)
                        return app.retro_terminal.type_text(f"RSA key pair with name \"{rsa_name}\" already exists. do you want to overwrite the existing file? : (y/n)")
                    else:
                        app.retro_terminal.type_text("Generating RSA keys...")
                        key_utils.generate_rsa_keypair(rsa_name,rsa_dir)
                        rsa_str = app.str_rsa_files()
                        return app.retro_terminal.type_text(f"{rsa_str}\nSuccessfully generated RSA key pair with name \"{rsa_name}\"")
                else:
                    return app.retro_terminal.type_text("You have to specify the name of the RSA key pair to be generated.")
            else:
                return app.retro_terminal.type_text("You have to select a directory for RSA key pairs first.\n"
                                                    "you can select directory using this command's parameter --setdir ")
        if "setdir" in keys:
            path = kwargs.get("setdir")
            if os.path.exists(path):
                config = utils.load_config()
                config["rsa_directory"] = path
                utils.dump_config(config)
                app.load_rsa_keys(add_prompt=False,tprint=True)
                app.rsa_file = None
                return app.retro_terminal.type_text(f"Successfully set \"{path}\" as RSA directory.")
            else:
                return app.retro_terminal.type_text("Path invalid or does not exists.")
        if "set" in keys:
            fname = kwargs.get('set')
            return app.select_rsa_key_by_name(fname)
        if "show" in keys:
            config = utils.load_config()
            rsa_dir = config.get('rsa_directory')
            if rsa_dir:
                if os.path.exists(rsa_dir):
                    app.retro_terminal.type_text(f"RSA directory: \"{rsa_dir}\"")
                    rsa_str = app.str_rsa_files()
                    app.retro_terminal.type_text(rsa_str)
                else:
                    app.retro_terminal.type_text("Select an RSA directory first.")
            else:
                app.retro_terminal.type_text("Select an RSA directory first.")

@command(name="set-preference",aliases=["preference","prefer"])
def set_preference(app,window_mode=None,ui_mode=None,*args,**kwargs):
    config = utils.load_config()
    pref = config.get("preferences")
    default = kwargs.get("default")
    if default:
        ui = "gui"
        window = "normal"
        app.retro_terminal.type_text(f"Setting window preference as '{window}'")
        app.retro_terminal.type_text(f"Setting ui preference as '{ui}'")
        pref['window_mode'] = window
        pref['ui_mode'] = ui
        config['preferences'] = pref
        utils.dump_config(config)
        app.init_preferences()
        return app.retro_terminal.type_text("Successfully saved preferences to default.")
    w_modes = ["fullscreen","maximize","normal","small"]
    u_modes = ["terminal","gui"]
    change_flag = False
    if not (window_mode or ui_mode):
        if kwargs:
            keys = [x.lower() for x in kwargs.keys()]
            window = kwargs.get('window')
            ui = kwargs.get('ui')
            w_condition = window in w_modes
            u_condition = ui in u_modes
            if not (u_condition or w_condition):
                return show_help(app,'preference')
            else:
                if w_condition:
                    window = window.lower()
                    pref['window_mode'] = window
                    app.retro_terminal.type_text(f"Setting window preference as '{window}'")
                if u_condition:
                    ui = ui.lower()
                    pref['ui_mode'] = ui
                    app.retro_terminal.type_text(f"Setting ui preference as '{ui}'")
                config['preferences'] = pref
                utils.dump_config(config)
                app.init_preferences()
                return app.retro_terminal.type_text("Successfully saved preferences.")
        else:
            return show_help(app,'preference')
    else:
        window_mode = window_mode.lower() if window_mode else window_mode
        ui_mode = ui_mode.lower() if ui_mode else ui_mode
        w_condition = window_mode in w_modes
        u_condition = ui_mode in u_modes
        if not (w_condition or u_condition):
            return show_help(app,'preference')
        if w_condition:
            pref['window_mode'] = window_mode
            app.retro_terminal.type_text(f"Setting window preference as '{window_mode}'")
        if u_condition:
            app.retro_terminal.type_text(f"Setting ui preference as '{ui_mode}'")
            pref['ui_mode'] = ui_mode
        config['preferences'] = pref
        utils.dump_config(config)
        app.init_preferences()
        return app.retro_terminal.type_text("Successfully saved preferences.")

@command(name="benchmark", aliases=["benchm", "bmark", "bm"])
def benchmark(app, *args, **kwargs):
    """Runs an encryption benchmark using the specified number of cores."""
    # === Step 1: Determine Number of Cores ===
    num_cores = utils.get_default_core_count()
    app.retro_terminal.type_text(f"Running benchmark with {num_cores} cores...")
    # === Step 2: Generate 100MB Test File ===
    test_file = os.path.abspath("./assets/benchmark_testfile.bin")
    output_file = os.path.abspath("./assets/benchmark_output.enc")
    if not os.path.exists(test_file):
        app.retro_terminal.type_text("Generating 100MB test file...")
        with open(test_file, "wb") as f:
            f.write(os.urandom(100 * 1024 * 1024))  # 100MB of random data
    app.retro_terminal.type_text(f"Starting encryption process...")
    # === Step 3: Measure Encryption Time ===
    start_time = time.time()
    key = "testing@123".encode()
    encryptor.encrypt_file(test_file,output_file,key)
    end_time = time.time()
    time_taken = end_time - start_time
    app.retro_terminal.type_text(f"Benchmark completed!")
    app.retro_terminal.type_text(f"Encryption Time: {time_taken:.4f} seconds")
    # Cleanup
    utils.del_file(test_file)
    utils.del_file(output_file)
    app.retro_terminal.type_text("Benchmark files cleaned up.")

@command(name="info",aliases=["showinfo","getinfo"])
def show_info(app,*args,**kwargs):
    cores = kwargs.get("cores") or kwargs.get("core") or kwargs.get("cpus") or kwargs.get("cpu") or kwargs.get("c")
    version = kwargs.get("version") or kwargs.get("ver") or kwargs.get("v")
    if not (cores or version):
        return show_help(app,'info')
    if cores:
        c_count = utils.get_default_core_count()
        app.retro_terminal.type_text(f"Enigmatrix encryption/decryption will use ({c_count}) cores of your cpu.")
    if version:
        app.retro_terminal.type_text(f"Current Enigmatrix version is : {VERSION}")


@command(name="run-as-admin", aliases=["admin", "sudo"])
def restart_with_admin(app, *args, **kwargs):
    """Restarts Enigmatrix with admin privileges."""
    script = sys.executable  # Path to the current Python interpreter or .exe
    params = " ".join(sys.argv)  # Preserve CLI args
    working_dir = app.retro_terminal.cwd  # Get the directory of the script
    if os.name == "nt":  # Windows
        if ctypes.windll.shell32.IsUserAnAdmin():
            app.retro_terminal.type_text("Already running as admin!")
            return
        # Relaunch with admin privileges
        response = ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, working_dir, 0)
        if response > 32:
            app.retro_terminal.type_text("Restarting Enigmatrix with admin privileges...")
            time.sleep(2)
            sys.exit()  # Exit the non-admin instance
        else:
            app.retro_terminal.type_text("Failed to restart with admin privileges!")
    else:  # Linux/macOS
        if os.geteuid() == 0:
            app.retro_terminal.type_text("Already running as root!")
            return
        # Relaunch with sudo, ensuring the correct working directory
        os.chdir(working_dir)
        os.execvp("sudo", ["sudo", script] + sys.argv)
        sys.exit()  # Exit the current process

@command(name="exit", aliases=["close"])
def exit_app(app, *args, **kwargs):
    app.close()
