# Backend server

The following commands are available

## Start up

To start the server:

```shell
python main.py --host "your-host" --matchmaker-port "your-matchmaker-port" --game-server-port "your-game-port" --lobby-size "n" --heartbeat-timeout "time in seconds" --num_tiles "number of gameboard tiles" --colour-selection-timeout "time in seconds"
```

To start the server in echo mode for testing, use the following command:

```shell
python main.py --host 127.0.0.1 --echo-port 9436
```