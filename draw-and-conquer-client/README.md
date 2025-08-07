## Available Scripts

In the project directory, you can run:

### `npm install`

Installs necessary dependencies to build the application.

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

## Configuring Server Connection

A file `.env` must be in this directory containing the following fields, without quotations to connect to a remote server.
If no `.env` file is added, or the appropriate fields are not filled out, the client will fall back to `localhost` on ports `9437` & `9438`.

```
REACT_APP_MATCH_MAKING_HOST="matchmaking server host"
REACT_APP_MATCH_MAKING_PORT="matchmaking server port"
REACT_APP_GAME_HOST="game server host"
REACT_APP_GAME_PORT="game server port"
```
