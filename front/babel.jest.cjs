module.exports = {
  presets: [
    ["@babel/preset-env", { targets: { node: "current" } }],
    ["@babel/preset-typescript", { allowDeclareFields: true }],
  ],
  overrides: [
    {
      test: /\.tsx$/,
      presets: [["@babel/preset-react", { runtime: "automatic" }]],
    },
  ],
};
