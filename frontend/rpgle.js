// Resaltado de sintaxis básico para RPGLE free-format (Monaco no lo trae por defecto).
window.registerRpgle = function (monaco) {
  monaco.languages.register({ id: "rpgle", extensions: [".rpgle", ".sqlrpgle"] });
  monaco.languages.setMonarchTokensProvider("rpgle", {
    ignoreCase: true,
    keywords: [
      "ctl-opt", "dcl-s", "dcl-c", "dcl-ds", "end-ds", "dcl-pr", "end-pr", "dcl-pi", "end-pi",
      "dcl-proc", "end-proc", "dcl-f", "dcl-subf", "dcl-parm", "if", "elseif", "else", "endif",
      "dow", "dou", "enddo", "for", "to", "downto", "by", "endfor", "select", "when", "other",
      "endsl", "monitor", "on-error", "endmon", "return", "leave", "iter", "exsr", "begsr",
      "endsr", "callp", "eval", "dsply", "read", "reade", "chain", "write", "update", "delete",
      "setll", "setgt", "open", "close", "exec", "sql", "and", "or", "not", "inz", "const",
      "value", "options", "export", "extproc", "likeds", "like", "dim", "qualified", "template",
    ],
    types: ["char", "varchar", "packed", "zoned", "int", "uns", "ind", "date", "time", "timestamp", "pointer", "float", "bindec", "graph", "ucs2"],
    tokenizer: {
      root: [
        [/^\*\*free/, "keyword.directive"],
        [/\/\/.*$/, "comment"],
        [/'([^']|'')*'/, "string"],
        [/%[a-z]+/, "predefined"],
        [/\*[a-z]+/, "constant"],
        [/\d+(\.\d+)?/, "number"],
        [/[a-z_][\w-]*/, { cases: { "@keywords": "keyword", "@types": "type", "@default": "identifier" } }],
        [/[;:(),=+\-*/<>]/, "delimiter"],
      ],
    },
  });
  monaco.languages.setLanguageConfiguration("rpgle", {
    comments: { lineComment: "//" },
    brackets: [["(", ")"]],
    autoClosingPairs: [{ open: "(", close: ")" }, { open: "'", close: "'" }],
  });
};
