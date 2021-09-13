<a id="packages.valory.connections.abci.connection"></a>

# packages.valory.connections.abci.connection

Connection to interact with an ABCI server.

<a id="packages.valory.connections.abci.connection._TendermintABCISerializer"></a>

## `_`TendermintABCISerializer Objects

```python
class _TendermintABCISerializer()
```

(stateless) utility class to encode/decode messages for the communication with Tendermint.

<a id="packages.valory.connections.abci.connection._TendermintABCISerializer.encode_varint"></a>

#### encode`_`varint

```python
@classmethod
def encode_varint(cls, number: int) -> bytes
```

Encode a number in varint coding.

<a id="packages.valory.connections.abci.connection._TendermintABCISerializer.decode_varint"></a>

#### decode`_`varint

```python
@classmethod
def decode_varint(cls, buffer: BytesIO) -> int
```

Decode a number from its varint coding.

<a id="packages.valory.connections.abci.connection._TendermintABCISerializer.write_message"></a>

#### write`_`message

```python
@classmethod
def write_message(cls, message: Response) -> bytes
```

Write a message in a buffer.

<a id="packages.valory.connections.abci.connection._TendermintABCISerializer.read_messages"></a>

#### read`_`messages

```python
@classmethod
def read_messages(cls, buffer: BytesIO, message_cls: Type) -> Request
```

Return an iterator over the messages found in the `reader` buffer.

<a id="packages.valory.connections.abci.connection.TcpServerChannel"></a>

## TcpServerChannel Objects

```python
class TcpServerChannel()
```

TCP server channel to handle incoming communication from the Tendermint node.

<a id="packages.valory.connections.abci.connection.TcpServerChannel.__init__"></a>

#### `__`init`__`

```python
def __init__(target_skill_id: PublicId, address: str, port: int, logger: Optional[Logger] = None)
```

Initialize the TCP server.

**Arguments**:

- `target_skill_id`: the public id of the target skill.
- `address`: the listen address.
- `port`: the port to listen from.
- `logger`: the logger.

<a id="packages.valory.connections.abci.connection.TcpServerChannel.is_stopped"></a>

#### is`_`stopped

```python
@property
def is_stopped() -> bool
```

Check that the channel is stopped.

<a id="packages.valory.connections.abci.connection.TcpServerChannel.connect"></a>

#### connect

```python
async def connect(loop: AbstractEventLoop) -> None
```

Connect.

Upon TCP Channel connection, start the TCP Server asynchronously.

**Arguments**:

- `loop`: asyncio event loop

<a id="packages.valory.connections.abci.connection.TcpServerChannel.disconnect"></a>

#### disconnect

```python
async def disconnect() -> None
```

Disconnect the channel

<a id="packages.valory.connections.abci.connection.TcpServerChannel.receive_messages"></a>

#### receive`_`messages

```python
async def receive_messages(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None
```

Receive incoming messages.

<a id="packages.valory.connections.abci.connection.TcpServerChannel.get_message"></a>

#### get`_`message

```python
async def get_message() -> Envelope
```

Get a message from the queue.

<a id="packages.valory.connections.abci.connection.TcpServerChannel.send"></a>

#### send

```python
async def send(envelope: Envelope) -> None
```

Send a message.

<a id="packages.valory.connections.abci.connection.TendermintParams"></a>

## TendermintParams Objects

```python
class TendermintParams()
```

Tendermint node parameters.

<a id="packages.valory.connections.abci.connection.TendermintParams.__init__"></a>

#### `__`init`__`

```python
def __init__(proxy_app: str, rpc_laddr: str, p2p_laddr: str, p2p_seeds: List[str], consensus_create_empty_blocks: bool, home: Optional[str] = None)
```

Initialize the parameters to the Tendermint node.

**Arguments**:

- `proxy_app`: ABCI address.
- `rpc_laddr`: RPC address.
- `p2p_laddr`: P2P address.
- `p2p_seeds`: P2P seeds.
- `consensus_create_empty_blocks`: if true, Tendermint node creates empty blocks.
- `home`: Tendermint's home directory.

<a id="packages.valory.connections.abci.connection.TendermintNode"></a>

## TendermintNode Objects

```python
class TendermintNode()
```

A class to manage a Tendermint node.

<a id="packages.valory.connections.abci.connection.TendermintNode.__init__"></a>

#### `__`init`__`

```python
def __init__(params: TendermintParams, logger: Optional[Logger] = None)
```

Initialize a Tendermint node.

**Arguments**:

- `params`: the parameters.
- `logger`: the logger.

<a id="packages.valory.connections.abci.connection.TendermintNode.init"></a>

#### init

```python
def init() -> None
```

Initialize Tendermint node.

<a id="packages.valory.connections.abci.connection.TendermintNode.start"></a>

#### start

```python
def start() -> None
```

Start a Tendermint node process.

<a id="packages.valory.connections.abci.connection.TendermintNode.stop"></a>

#### stop

```python
def stop() -> None
```

Stop a Tendermint node process.

<a id="packages.valory.connections.abci.connection.ABCIServerConnection"></a>

## ABCIServerConnection Objects

```python
class ABCIServerConnection(Connection)
```

ABCI server.

<a id="packages.valory.connections.abci.connection.ABCIServerConnection.__init__"></a>

#### `__`init`__`

```python
def __init__(**kwargs: Any) -> None
```

Initialize the connection.

**Arguments**:

- `kwargs`: keyword arguments passed to component base

<a id="packages.valory.connections.abci.connection.ABCIServerConnection.connect"></a>

#### connect

```python
async def connect() -> None
```

Set up the connection.

In the implementation, remember to update 'connection_status' accordingly.

<a id="packages.valory.connections.abci.connection.ABCIServerConnection.disconnect"></a>

#### disconnect

```python
async def disconnect() -> None
```

Tear down the connection.

In the implementation, remember to update 'connection_status' accordingly.

<a id="packages.valory.connections.abci.connection.ABCIServerConnection.send"></a>

#### send

```python
async def send(envelope: Envelope) -> None
```

Send an envelope.

**Arguments**:

- `envelope`: the envelope to send.

<a id="packages.valory.connections.abci.connection.ABCIServerConnection.receive"></a>

#### receive

```python
async def receive(*args: Any, **kwargs: Any) -> Optional[Envelope]
```

Receive an envelope. Blocking.

**Arguments**:

- `args`: arguments to receive
- `kwargs`: keyword arguments to receive

**Returns**:

the envelope received, if present.  # noqa: DAR202
