const path = require('path');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const webpack = require("webpack");
const dotEnv = require("dotenv");

module.exports = {
    entry: [
      './src/index.tsx' // The entry point
    ],
    output: {
      //path: (__dirname = 'build'), // folder webpack should output files to
      path: __dirname + '/build',
      publicPath: '/', // path to build directory
      filename: 'bundle.js' // file to output js to
    },
    plugins: [
      new MiniCssExtractPlugin(),
      new webpack.DefinePlugin({
        "process.env": getEnvironmentVariables(),
      }),
    ],
    module: {
        rules: [
          {
            test: /\.(js|jsx|tsx|ts)$/,
            exclude: /node_modules/,
            use: [
                {
                    loader: 'babel-loader',
                    options: {
                        plugins: [
                            ['import', { libraryName: "antd", style: true }]
                          ]
                    }
                },
                {
                    loader: 'ts-loader',
                    options: {
                        configFile: path.resolve('./tsconfig.json'),
                    },
                },
            ],
          },
          {
            test: /((?!\.module).)*crvss$/,
            use: [MiniCssExtractPlugin.loader, 'css-loader'],
          },
          {
            test: /\.css$/,
            use: [{loader: 'style-loader'}, 
                  {
                    loader: 'css-loader',
                    //options: { modules: true },
                  }],
          },
          {
            test: /\.(js|jsx|ts|tsx)$/,
            exclude: /node_modules/,
            use: ['eslint-loader']
          },
          {
            test: /\.(png|jpg|gif)$/,
            use: [
              {
                loader: 'file-loader',
                options: {}
              }
            ]
          }
        ]
    },
    resolve: {
      // makes it so you don't have to
      // write .js and .jsx at the end of imports
      extensions: ['.js', '.jsx', '.ts', '.tsx']
    },
    devServer: {
      contentBase: './build', // dev server folder to use
      proxy: {
          '/api/**': {
              target: 'http://127.0.0.1:8000/',
              secure: false,
              changeOrigin: true
          }
      },
      overlay: true,
      historyApiFallback: true,
      headers: { 
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept"
      }
    }
  }

  function getEnvironmentVariables() {
    const defaultEnv = dotEnv.config({ path: path.resolve(process.cwd(), ".env.default") }).parsed;
    const env = Object.assign({}, defaultEnv, dotEnv.config().parsed);
  
    return Object.keys(env).reduce((prev, next) => {
      prev[next] = JSON.stringify(env[next]);
  
      return prev;
    }, {});
  }
  