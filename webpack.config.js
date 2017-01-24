var path = require('path');

const buildPath = 'bogo/static/build';

const config = {
  entry: './bogo/static/jsx/ui.jsx',
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
