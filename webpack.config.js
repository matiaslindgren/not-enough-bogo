var path = require('path');

const buildPath = 'app/src/static/build';

const config = {
  entry: './app/src/static/jsx/ui.jsx',
  output: {
    path: path.resolve(__dirname,  buildPath),
    filename: 'ui.min.js'
  },
  module: {
    loaders: [
      {
        test: /\.jsx$/,
        loader: 'babel-loader',
        exclude: /node_modules/
      }
    ]
  }
};

module.exports = config;
