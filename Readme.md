# EPUB Generator | EPUBジェネレーター

This project converts text files downloaded from the ["小説家になろう"](https://syosetu.com/) website into vertically written EPUB files.
このプロジェクトは、["小説家になろう"](https://syosetu.com/) サイトからダウンロードしたテキストファイルを縦書きのEPUBファイルに変換します。
This project is a work in progress and may not support all features of the EPUB format.
This project also supports files from [Aozora Bunko](https://www.aozora.gr.jp/), though this feature is not fully tested.
このプロジェクトは、[青空文庫](https://www.aozora.gr.jp/) のファイルにも対応していますが、未検証です。

## Features | 特徴

- Converts plain text files into EPUB format.
  テキストファイルをEPUB形式に変換します。
- Supports vertical writing, suitable for Japanese novels.
  日本の小説に適した縦書きに対応しています。
- Easy to use with minimal setup.
  簡単なセットアップで使用可能です。

## Requirements | 必要条件

- Python 3.8 or higher
  Python 3.8以上
- Required Python libraries (install via `requirements.txt`)
  必要なPythonライブラリ（`requirements.txt`からインストール）

## Installation | インストール

1. Clone this repository:
   リポジトリをクローンします。

   ```bash
   git clone https://github.com/mostlyfine/epub-generator.git
   cd epub-generator
   ```

2. Install dependencies:
   依存関係をインストールします。

   ```bash
   pip install -r requirements.txt
   ```

## Usage | 使い方

1. Place the downloaded text file from "小説家になろう" in the directory specified in the config file.
   「小説家になろう」からダウンロードしたテキストファイルを設定ファイルで指定したディレクトリに配置します。

2. Run the script to generate the EPUB file:
   スクリプトを実行してEPUBファイルを生成します。

   ```bash
   python generate.py [config.yaml]
   ```

3. The generated EPUB file will be saved with the filename specified in the config file.
   生成されたEPUBファイルは設定ファイルに指定されたファイル名で保存されます。

## Usage for Docker | Dockerを使用する場合

If you prefer to use Docker, you can build and run the Docker image as follows:
Dockerを使用する場合は、以下の手順でDockerイメージをビルドして実行できます。

 ```bash
docker build -t epub-generator .
docker run --rm -it -v $(pwd):/app/ epub-generator [config.yaml]
```

You can also use the provided shell script `epub-generator.sh` for convenience:
以下のシェルスクリプト `epub-generator.sh` を使用することもできます。

```bash
./epub-generator.sh [config.yaml]
```
epub-generator.shを実行することで、同様のことができます。


## Configuration | 設定

You can customize the following options:
以下のオプションをカスタマイズできます。

- **Font family**: Adjust the font family for vertical writing.
  **フォントファミリー**: 縦書き用のフォントファミリーを調整します。
- **Line spacing**: Modify the spacing between lines.
  **行間**: 行間を変更します。
- **Metadata**: Add title, author, and other metadata to the EPUB file.
  **メタデータ**: タイトル、著者名、その他のメタデータをEPUBファイルに追加します。

## License | ライセンス

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
このプロジェクトはMITライセンスの下で提供されています。詳細は[LICENSE](LICENSE)ファイルをご覧ください。

## Acknowledgments | 謝辞

- "小説家になろう" for providing the source content.
  ソースコンテンツを提供している「小説家になろう」に感謝します。
- Contributors and open-source libraries used in this project.
  このプロジェクトで使用されている貢献者およびオープンソースライブラリに感謝します。

Enjoy reading your favorite novels in a beautifully formatted vertical EPUB!
美しくフォーマットされた縦書きEPUBでお気に入りの小説をお楽しみください！
