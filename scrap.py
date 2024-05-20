#//////////////////////////////////////
#sender.py

import socket
import api
import argparse
import api

# region Predefined

# The following are for convenience. You can use them to build expressions.
pi_c = api.NAMED_CONSTANTS.PI
tau_c = api.NAMED_CONSTANTS.TAU
e_c = api.NAMED_CONSTANTS.E

add_b = api.BINARY_OPERATORS.ADD
sub_b = api.BINARY_OPERATORS.SUB
mul_b = api.BINARY_OPERATORS.MUL
div_b = api.BINARY_OPERATORS.DIV
mod_b = api.BINARY_OPERATORS.MOD
pow_b = api.BINARY_OPERATORS.POW

neg_u = api.UNARY_OPERATORS.NEG
pos_u = api.UNARY_OPERATORS.POS

sin_f = api.FUNCTIONS.SIN
cos_f = api.FUNCTIONS.COS
tan_f = api.FUNCTIONS.TAN
sqrt_f = api.FUNCTIONS.SQRT
log_f = api.FUNCTIONS.LOG
max_f = api.FUNCTIONS.MAX
min_f = api.FUNCTIONS.MIN
pow_f = api.FUNCTIONS.POW
rand_f = api.FUNCTIONS.RAND

# endregion


def process_response(response: api.CalculatorHeader) -> None:
    if response.is_request:
        raise api.CalculatorClientError("Got a request instead of a response")
    if response.status_code == api.CalculatorHeader.STATUS_OK:
        result, steps = api.data_to_result(response)
        print("Result:", result)
        if steps:
            print("Steps:")
            expr, first, *rest = steps
            print(f"{expr} = {first}", end="\n"*(not bool(rest)))
            if rest:
                print(
                    "".join(map(lambda v: f"\n{' ' * len(expr)} = {v}", rest)))
    elif response.status_code == api.CalculatorHeader.STATUS_CLIENT_ERROR:
        err = api.data_to_error(response)
        raise api.CalculatorClientError(err)
    elif response.status_code == api.CalculatorHeader.STATUS_SERVER_ERROR:
        err = api.data_to_error(response)
        raise api.CalculatorServerError(err)
    else:
        raise api.CalculatorClientError(
            f"Unknown status code: {response.status_code}")


def client(server_address: tuple[str, int], expression: api.Expression, show_steps: bool = False, cache_result: bool = False, cache_control: int = api.CalculatorHeader.MAX_CACHE_CONTROL) -> None:
    server_prefix = f"{{{server_address[0]}:{server_address[1]}}}"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(server_address)
        print(f"{server_prefix} Connection established")

        try:
            request = api.CalculatorHeader.from_expression(
                expression, show_steps, cache_result, cache_control)

            request = request.pack()
            print(f"{server_prefix} Sending request of length {len(request)} bytes")
            client_socket.sendall(request)

            response = client_socket.recv(api.BUFFER_SIZE)
            print(f"{server_prefix} Got response of length {len(response)} bytes")
            response = api.CalculatorHeader.unpack(response)
            process_response(response)

        except api.CalculatorError as e:
            print(f"{server_prefix} Got error: {str(e)}")
        except Exception as e:
            print(f"{server_prefix} Unexpected error: {str(e)}")
    print(f"{server_prefix} Connection closed")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="A Calculator Client.")

    arg_parser.add_argument("-p", "--port", type=int,
                            default=api.DEFAULT_SERVER_PORT, help="The port to connect to.")
    arg_parser.add_argument("-H", "--host", type=str,
                            default=api.DEFAULT_SERVER_HOST, help="The host to connect to.")

    args = arg_parser.parse_args()

    host = args.host
    port = args.port

    # Example expressions: (uncomment one of them for your needs)
    # (1) '(sin(max(2, 3 * 4, 5, 6 * ((7 * 8) / 9), 10 / 11)) / 12) * 13' = -0.38748277824137206
    #expr = mul_b(div_b(sin_f(max_f(2, mul_b(3, 4), 5, mul_b(6, div_b(mul_b(7, 8), 9)), div_b(10, 11))), 12), 13)  # (1)

    # (2) '(max(2, 3) + 3)' = 6
    expr = add_b(max_f(2, 3), 3) # (2)

    # (3) '3 + ((4 * 2) / ((1 - 5) ** (2 ** 3)))' = 3.0001220703125
    #expr = add_b(3, div_b(mul_b(4, 2), pow_b(sub_b(1, 5), pow_b(2, 3)))) # (3)

    # (4) '((1 + 2) ** (3 * 4)) / (5 * 6)' = 17714.7
    #expr = div_b(pow_b(add_b(1, 2), mul_b(3, 4)), mul_b(5, 6)) # (4)

    # (5) '-(-((1 + (2 + 3)) ** -(4 + 5)))' = 9.92290301275212e-08
    # expr = neg_u(neg_u(pow_b(add_b(1, add_b(2, 3)), neg_u(add_b(4, 5))))) # (5)

    # (6) 'max(2, (3 * 4), log(e), (6 * 7), (9 / 8))' = 42
    # expr = max_f(2, mul_b(3, 4), log_f(e_c), mul_b(6, 7), div_b(9, 8)) # (6)

    # Change the following values according to your needs:

    show_steps = True  # Request the steps of the calculation
    cache_result = True  # Request to cache the result of the calculation
    # If the result is cached, this is the maximum age of the cached response
    # that the client is willing to accept (in seconds)
    cache_control = 2**16 - 1

    client((host, port), expr, show_steps,
           cache_result, cache_control)

#/////////////////////////////
#Server.py

import numbers
import api
import argparse
import socket
import threading

CACHE_POLICY = True  # whether to cache responses or not
# the maximum time that the response can be cached for (in seconds)
CACHE_CONTROL = 2 ** 16 - 1


def calculate(expression: api.Expr, steps: list[str] = []) -> tuple[numbers.Real, list[api.Expression]]:
    '''
    Function which calculates the result of an expression and returns the result and the steps taken to calculate it.
    The function recursively descends into the expression tree and calculates the result of the expression.
    Each expression wraps the result of its subexpressions in parentheses and adds the result to the steps list.
    '''
    expr = api.type_fallback(expression)
    const = None
    if isinstance(expr, api.Constant) or isinstance(expr, api.NamedConstant):
        const = expr
    elif isinstance(expr, api.BinaryExpr):
        left_steps, right_steps = [], []
        left, left_steps = calculate(expr.left_operand, left_steps)
        for step in left_steps[:-1]:
            steps.append(api.BinaryExpr(
                step, expr.operator, expr.right_operand))
        right, left_steps = calculate(expr.right_operand, right_steps)
        for step in right_steps[:-1]:
            steps.append(api.BinaryExpr(left, expr.operator, step))
        steps.append(api.BinaryExpr(left, expr.operator, right))
        const = api.Constant(expr.operator.function(left, right))
        steps.append(const)
    elif isinstance(expr, api.UnaryExpr):
        operand_steps = []
        operand, operand_steps = calculate(expr.operand, operand_steps)
        for step in operand_steps[:-1]:
            steps.append(api.UnaryExpr(expr.operator, step))
        steps.append(api.UnaryExpr(expr.operator, operand))
        const = api.Constant(expr.operator.function(operand))
        steps.append(const)
    elif isinstance(expr, api.FunctionCallExpr):
        args = []
        for arg in expr.args:
            arg_steps = []
            arg, arg_steps = calculate(arg, arg_steps)
            for step in arg_steps[:-1]:
                steps.append(api.FunctionCallExpr(expr.function, *
                             (args + [step] + expr.args[len(args) + 1:])))
            args.append(arg)
        steps.append(api.FunctionCallExpr(expr.function, *args))
        const = api.Constant(expr.function.function(*args))
        steps.append(const)
    else:
        raise TypeError(f"Unknown expression type: {type(expr)}")
    return const.value, steps


def process_request(request: api.CalculatorHeader) -> api.CalculatorHeader:
    '''
    Function which processes a CalculatorRequest and builds a CalculatorResponse.
    '''
    result, steps = None, []
    try:
        if request.is_request:
            expr = api.data_to_expression(request)
            result, steps = calculate(expr, steps)
        else:
            raise TypeError("Received a response instead of a request")
    except Exception as e:
        return api.CalculatorHeader.from_error(e, api.CalculatorHeader.STATUS_CLIENT_ERROR, CACHE_POLICY, CACHE_CONTROL)

    if request.show_steps:
        steps = [api.stringify(step, add_brackets=True) for step in steps]
    else:
        steps = []

    return api.CalculatorHeader.from_result(result, steps, CACHE_POLICY, CACHE_CONTROL)


def server(host: str, port: int) -> None:
    # socket(socket.AF_INET, socket.SOCK_STREAM)
    # (1) AF_INET is the address family for IPv4 (Address Family)
    # (2) SOCK_STREAM is the socket type for TCP (Socket Type) - [SOCK_DGRAM is the socket type for UDP]
    # Note: context manager ('with' keyword) closes the socket when the block is exited
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # SO_REUSEADDR is a socket option that allows the socket to be bound to an address that is already in use.
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Prepare the server socket
        # * Fill in start (1)

        # Binding the server socket to the given port and ip
        server_socket.bind((host, port))

        # Making the port listen for any incoming internet traffic
        server_socket.listen(1)

        # * Fill in end (1)

        threads = []
        print(f"Listening on {host}:{port}")

        while True:
            try:
                # Establish connection with client.
                # * Fill in start (2)

                # Accepting the new incoming connection
                client_socket, address = server_socket.accept()

                # * Fill in end (2)

                # Create a new thread to handle the client request
                thread = threading.Thread(target=client_handler, args=(
                    client_socket, address))
                thread.start()
                threads.append(thread)
            except KeyboardInterrupt:
                print("Shutting down...")
                break

        for thread in threads:  # Wait for all threads to finish
            thread.join()


def client_handler(client_socket: socket.socket, client_address: tuple[str, int]) -> None:
    '''
    Function which handles client requests
    '''
    client_addr = f"{client_address[0]}:{client_address[1]}"
    client_prefix = f"{{{client_addr}}}"
    with client_socket:  # closes the socket when the block is exited
        print(f"Conection established with {client_addr}")
        while True:
            # * Fill in start (3)

            # Receiving the Data from the client socket. Maximum buffer size: 8192 Bytes
            data = client_socket.recv(int(api.BUFFER_SIZE / 8))

            # * Fill in end (3)
            if not data:
                break
            try:

                try:
                    request = api.CalculatorHeader.unpack(data)
                except Exception as e:
                    raise api.CalculatorClientError(
                        f'Error while unpacking request: {e}') from e

                print(f"{client_prefix} Got request of length {len(data)} bytes")

                response = process_request(request)

                response = response.pack()
                print(
                    f"{client_prefix} Sending response of length {len(response)} bytes")

                # * Fill in start (4)

                # Sending back the entire response all at once
                client_socket.sendall(response)

                # * Fill in end (4)

            except Exception as e:
                print(f"Unexpected server error: {e}")
                client_socket.sendall(api.CalculatorHeader.from_error(
                    e, api.CalculatorHeader.STATUS_SERVER_ERROR, CACHE_POLICY, CACHE_CONTROL).pack())
            print(f"{client_prefix} Connection closed")


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='A Calculator Server.')

    arg_parser.add_argument('-p', '--port', type=int,
                            default=api.DEFAULT_SERVER_PORT, help='The port to listen on.')
    arg_parser.add_argument('-H', '--host', type=str,
                            default=api.DEFAULT_SERVER_HOST, help='The host to listen on.')

    args = arg_parser.parse_args()

    host = args.host
    port = args.port

    server(host, port)

#//////////////////////////////////////////////////////////////////////////////////
#proxy.py

import api
import argparse
import threading
import socket
import time
import math

cache: dict[tuple[bytes, bool], api.CalculatorHeader] = {}
INDEFINITE = api.CalculatorHeader.MAX_CACHE_CONTROL


def process_request(request: api.CalculatorHeader, server_address: tuple[str, int]) -> tuple[
    api.CalculatorHeader, int, int, bool, bool, bool]:
    '''
    Function which processes the client request if specified we cache the result
    Returns the response, the time remaining before the server deems the response stale, the time remaining before the client deems the response stale, whether the response returned was from the cache, whether the response was stale, and whether we cached the response
    If the request.cache_control is 0, we don't use the cache and send a new request to the server. (like a reload)
    If the request.cache_control < time() - cache[request].unix_time_stamp, the client doesn't allow us to use the cache and we send a new request to the server.
    If the cache[request].cache_control is 0, the response must not be cached.
    '''
    if not request.is_request:
        raise TypeError("Received a response instead of a request")

    data = request.data
    server_time_remaining = None
    client_time_remaining = None
    was_stale = False
    cached = False
    # Check if the data is in the cache, if the requests cache-control is 0 we must not use the cache and request a new response
    if ((data, request.show_steps) in cache) and (request.cache_control != 0):
        response = cache[(data, request.show_steps)]
        current_time = int(time.time())
        age = current_time - response.unix_time_stamp
        res_cc = response.cache_control if response.cache_control != INDEFINITE else math.inf
        req_cc = request.cache_control if request.cache_control != INDEFINITE else math.inf
        server_time_remaining = res_cc - age
        client_time_remaining = req_cc - age
        # response is still 'fresh' both for the client and the server
        if server_time_remaining > 0 and client_time_remaining > 0:
            return response, server_time_remaining, client_time_remaining, True, False, False
        else:  # response is 'stale'
            was_stale = True

    # Request is not in the cache or the response is 'stale' so we need to send a new request to the server and cache the response
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        try:
            server_socket.connect(server_address)
        except ConnectionRefusedError:
            raise api.CalculatorServerError(
                "Connection refused by server and the request was not in the cache/it was stale")
        server_socket.sendall(request.pack())

        response = server_socket.recv(api.BUFFER_SIZE)

        try:
            response = api.CalculatorHeader.unpack(response)
        except Exception as e:
            raise api.CalculatorClientError(
                f'Error while unpacking request: {e}') from e

        if response.is_request:
            raise TypeError("Received a request instead of a response")

        current_time = int(time.time())
        age = current_time - response.unix_time_stamp
        res_cc = response.cache_control if response.cache_control != INDEFINITE else math.inf
        req_cc = request.cache_control if request.cache_control != INDEFINITE else math.inf
        server_time_remaining = res_cc - age
        client_time_remaining = req_cc - age
        # Cache the response if all sides agree to cache it
        if request.cache_result and response.cache_result and (server_time_remaining > 0 and client_time_remaining > 0):
            cache[(data, request.show_steps)] = response
            cached = True

    return response, server_time_remaining, client_time_remaining, False, was_stale, cached


def proxy(proxy_address: tuple[str, int], server_adress: tuple[str, int]) -> None:
    # socket(socket.AF_INET, socket.SOCK_STREAM)
    # (1) AF_INET is the address family for IPv4 (Address Family)
    # (2) SOCK_STREAM is the socket type for TCP (Socket Type) - [SOCK_DGRAM is the socket type for UDP]
    # Note: context manager ('with' keyword) closes the socket when the block is exited
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as proxy_socket:
        # SO_REUSEADDR is a socket option that allows the socket to be bound to an address that is already in use.
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Prepare the proxy socket
        # * Fill in start (1)

        # Binding the server socket to the given port and ip
        proxy_socket.bind(proxy_address)

        # Making the port listen for any incoming internet traffic
        proxy_socket.listen(1)

        # * Fill in end (1)

        threads = []
        print(f"Listening on {proxy_address[0]}:{proxy_address[1]}")

        while True:
            try:
                # Establish connection with client.
                # * Fill in start (2)

                # Accepting the new incoming connection
                client_socket, client_address = proxy_socket.accept()

                # * Fill in end (2)

                # Create a new thread to handle the client request
                thread = threading.Thread(target=client_handler, args=(
                    client_socket, client_address, server_adress))
                thread.start()
                threads.append(thread)
            except KeyboardInterrupt:
                print("Shutting down...")
                break

        for thread in threads:  # Wait for all threads to finish
            thread.join()


def client_handler(client_socket: socket.socket, client_address: tuple[str, int],
                   server_address: tuple[str, int]) -> None:
    '''
    Function which handles client requests
    '''
    client_prefix = f"{{{client_address[0]}:{client_address[1]}}}"
    with client_socket:  # closes the socket when the block is exited
        print(f"{client_prefix} Connected established")
        while True:
            # Receive data from the client

            # * Fill in start (3)

            # Receiving the Data from the client socket. Maximum buffer size: 8192 Bytes
            data = client_socket.recv(int(api.BUFFER_SIZE / 8))

            # * Fill in end (3)

            if not data:
                break
            try:
                # Process the request
                try:
                    request = api.CalculatorHeader.unpack(data)
                except Exception as e:
                    raise api.CalculatorClientError(
                        f'Error while unpacking request: {e}') from e

                print(f"{client_prefix} Got request of length {len(data)} bytes")

                response, server_time_remaining, client_time_remaining, cache_hit, was_stale, cached = process_request(
                    request, server_address)

                if cache_hit:
                    print(f"{client_prefix} Cache hit", end=" ,")
                elif was_stale:
                    print(f"{client_prefix} Cache miss, stale response", end=" ,")
                elif cached:
                    print(f"{client_prefix} Cache miss, response cached", end=" ,")
                else:
                    print(
                        f"{client_prefix} Cache miss, response not cached", end=" ,")
                print(
                    f"server time remaining: {server_time_remaining:.2f}, client time remaining: {client_time_remaining:.2f}")

                response = response.pack()
                print(
                    f"{client_prefix} Sending response of length {len(response)} bytes")

                # Send the response back to the client
                # * Fill in start (4)

                # Sending back the entire response all at once
                client_socket.sendall(response)

                # * Fill in end (4)

            except Exception as e:
                print(f"Unexpected server error: {e}")
                client_socket.sendall(api.CalculatorHeader.from_error(api.CalculatorServerError(
                    "Internal proxy error", e), api.CalculatorHeader.STATUS_SERVER_ERROR, False, 0).pack())
            print(f"{client_prefix} Connection closed")


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='A Calculator Server.')

    arg_parser.add_argument('-pp', '--proxy_port', type=int, dest='proxy_port',
                            default=api.DEFAULT_PROXY_PORT, help='The port that the proxy listens on.')
    arg_parser.add_argument('-ph', '--proxy_host', type=str, dest='proxy_host',
                            default=api.DEFAULT_PROXY_HOST, help='The host that the proxy listens on.')
    arg_parser.add_argument('-sp', '--server_port', type=int, dest='server_port',
                            default=api.DEFAULT_SERVER_PORT, help='The port that the server listens on.')
    arg_parser.add_argument('-sh', '--server_host', type=str, dest='server_host',
                            default=api.DEFAULT_SERVER_HOST, help='The host that the server listens on.')

    args = arg_parser.parse_args()

    proxy_host = args.proxy_host
    proxy_port = args.proxy_port
    server_host = args.server_host
    server_port = args.server_port

    proxy((proxy_host, proxy_port), (server_host, server_port))
