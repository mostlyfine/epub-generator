import sys
import os
import yaml
import glob
import re

from ebooklib import epub
import mimetypes

DEFAULT_LANGUAGE = 'ja'
INPUT_DIR = 'docs'
OUTPUT_FILE = 'output.epub'
COVER_IMAGE = 'cover.png'
CSS_FILE = 'style.css'
DEFAULT_CONFIG_FILE = 'config.yaml'
DEFAULT_DIRECTION = 'rtl'


def set_metadata(book, config):
    """
    EPUBのメタデータを設定する
    :param book: EPUB Book object
    :param config: Configuration dictionary
    """
    book.set_title(config['title'])
    book.add_author(config['author'])
    book.set_language(config.get('language', DEFAULT_LANGUAGE))
    book.direction = config.get('direction', DEFAULT_DIRECTION)
    book.set_identifier(f'urn:uuid:{os.urandom(16).hex()}')
    book.add_metadata('DC', 'description', config.get('description', ''))
    book.add_metadata('DC', 'publisher', config.get('publisher', ''))
    book.add_metadata('DC', 'date', config.get('date', ''))


def read_text_file(filepath):
    encodings_to_try = ['utf-8', 'cp932', 'shift_jis', 'euc-jp', 'iso-8859-1']

    for encode in encodings_to_try:
        try:
            with open(filepath, 'r', encoding=encode) as f:
                return f.read()
        except Exception:
            continue

    raise UnicodeDecodeError(f'{filepath} のエンコーディングを検出できませんでした。')


def create_content(book, config):

    lang = config.get('language', DEFAULT_LANGUAGE)
    input_dir = config.get('input_directory', INPUT_DIR)
    txt_files_unsorted = glob.glob(os.path.join(input_dir, '*.txt'))

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([\s\d_]+)', s)]
    txt_files = sorted(txt_files_unsorted, key=natural_sort_key)

    if not txt_files:
        print(f"'{input_dir}' に .txt ファイルが見つかりませんでした。")
        return

    css = get_css_file(config)

    toc_links = []  # 目次リンク (epub.Linkオブジェクト) を格納
    nav = epub.EpubNav()
    nav.add_item(css)
    book.add_item(nav)
    spine_items = [nav]

    for i, textfile in enumerate(txt_files):
        chapter_title = re.sub(
            r'^(エピソード)?[0-9_ ]+：?', '', os.path.splitext(os.path.basename(textfile))[0])
        chapter_no = f'chapter_{i+1}'

        print(f"Processing {textfile} as {chapter_title}: {chapter_no}")
        content_text = read_text_file(textfile)
        content_html = convert_to_html(
            chapter_title, content_text, book, config)
        chapter_file_name = f'{chapter_no}.xhtml'
        c = epub.EpubHtml(
            title=chapter_title, file_name=chapter_file_name, lang=lang)
        c.add_item(css)
        c.set_content(content_html)
        book.add_item(c)

        spine_items.append(c)
        toc_links.append(
            epub.Link(chapter_file_name, chapter_title, f"toc_chap_{i+1}"))

    book.toc = tuple(toc_links)
    book.add_item(epub.EpubNcx())
    book.spine = spine_items


def preprocess_text_content(text_content):
    """
    テキストコンテンツを事前処理する
    :param text_content: テキストコンテンツ
    :return: 処理されたテキストコンテンツ
    """
    # Windowsの改行コード(CRLF)をLFに統一し、3つ以上の連続改行を2つにまとめる
    processed_text = text_content.replace('\r\n', '\n')
    processed_text = re.sub(
        r'^[\t 　◇◆☆★〇○◎●△▲▽▼※〒〓]+$', '\n', processed_text, flags=re.MULTILINE)
    processed_text = re.sub(r'\n{3,}', '\n\n\n',
                            processed_text, flags=re.MULTILINE)
    return processed_text


def convert_to_html(chapter_title, text_content, book, config):
    """
    テキストコンテンツをHTMLに変換する
    :param text_content: テキストコンテンツ
    :param book: EPUB Book object
    :param config: Configuration dictionary
    :return: HTMLコンテンツ
    """
    processed_text = preprocess_text_content(text_content)

    html_paragraphs = [f'<h1>{chapter_title}</h1>']
    # 2つの改行で段落に分割
    for para_text in processed_text.strip().split('\n\n\n'):
        if para_text.strip():
            html_lines_in_paragraph = []
            # 段落内の各行に分割
            for single_line in para_text.split('\n'):
                if single_line.strip():
                    processed_html_line = convert_line_text_to_html(
                        single_line.strip(), book, config)
                    html_lines_in_paragraph.append(processed_html_line)

            if html_lines_in_paragraph:
                # 処理された行を<br />で結合し、<p>タグで囲む
                html_paragraphs.append(
                    '<p>' + '<br />'.join(html_lines_in_paragraph) + '</p>')

    return '\n'.join(html_paragraphs)


def convert_line_text_to_html(line_text, book, config):
    """
    1行のテキストを処理し、ルビ変換（行頭以外）、縦中横変換を行います。
    """
    input_dir = config.get('input_directory', INPUT_DIR)
    processed_line = line_text

    # 1. ルビ変換
    processed_line = convert_ruby_to_html(processed_line)

    # 2. 縦中横変換 ( [[...]] で囲まれた半角英数字記号2～4文字程度)
    def tcy_replace_callback(match):
        content = match.group(1)
        # 縦中横の対象とする文字種と長さをチェック
        if re.fullmatch(r'[a-zA-Z0-9.,\-:/+]{2,4}', content):
            return f'<span class="tcy">{content}</span>'
        return match.group(0)   # 条件に合わなければ元の文字列を返す (例: [[長すぎる文字列]])

    processed_line = re.sub(
        r'\[\[([a-zA-Z0-9.,\-:/+]{2,4}?)\]\]', tcy_replace_callback, processed_line)

    # 3. 画像の処理
    def add_image(match):
        # 画像のパスを取得し、imgタグを生成
        image_path = match.group(1)
        media_type, _ = mimetypes.guess_type(image_path)
        with open(f'{input_dir}/{image_path}', 'rb') as f:
            img_data = f.read()
        image = epub.EpubItem(
            uid=image_path, file_name=image_path, media_type=media_type, content=img_data)
        book.add_item(image)
        return f'<img src="{image_path}" alt="{image_path}"/>'

    processed_line = re.sub(
        r'［＃.*[（（](.+\.(png|jpe?g|gif|webp)).*[））].*］', add_image, processed_line)

    # 4. 改行処理など
    processed_line = re.sub(r'^[	 　＊\−\-ー]+$', '<br /><hr />', processed_line)
    processed_line = re.sub(
        r'^(第[一二三四五六七八九十0-9０-９]+部.*)$', r'<h3>\1</h3>', processed_line)
    processed_line = re.sub(
        r'^(第[一二三四五六七八九十0-9０-９]+章.*)$', r'<h4>\1</h4>', processed_line)

    processed_line = re.sub(r'［＃改(ページ|丁)］', '</p><p><br />', processed_line)
    processed_line = re.sub(r'［＃.+］', '', processed_line)

    return processed_line


def convert_ruby_to_html(text: str) -> str:
    """
    テキスト内の特定のルビ表記パターンをHTMLの<ruby>タグ形式に変換します。

    対応するパターンと優先順位:
    1.  括弧のルビ回避: `｜(テキスト)` または `|(テキスト)` -> `(テキスト)`
        (括弧の直前に縦線がある場合、ルビとして解釈せず縦線のみを削除)
    2.  縦線付き明示的ルビ: `｜ベーステキスト《ルビ》` または `|ベーステキスト《ルビ》`
        (全角または半角の縦線で始まり、ベーステキストの後に二重山括弧でルビが続く)
    3.  暗黙的なルビ（漢字 + 二重山括弧）: `漢字《ひらがな/カタカナ》`
        (漢字のベーステキストの後に二重山括弧でルビが続く。縦線は省略可能)
    4.  暗黙的なルビ（漢字 + 括弧）: `漢字(ひらがな/カタカナ)`
        (漢字のベーステキストの後に括弧でルビが続く。)

    Args:
        text: ルビ表記を含む入力文字列。

    Returns:
        HTMLの<ruby>タグに変換された文字列。
    """

    # 処理するパターンのリスト。優先順位の高い順に並べる。
    # 各要素は (コンパイル済み正規表現, 置換関数) のタプル。
    # 置換関数はマッチオブジェクトを受け取り、置換後の文字列を返す。
    patterns = [
        # パターン1: 括弧のルビ回避 (｜(テキスト) または |(テキスト))
        # 縦線と括弧内のテキストをキャプチャし、縦線を除去した括弧付きテキストに置換
        (re.compile(r'[｜|]\((.*?)\)'), lambda m: f'({m.group(1)})'),
        (re.compile(r'[｜|]（(.*?)）'), lambda m: f'({m.group(1)})'),

        # パターン2: 縦線付き明示的ルビ (｜ベーステキスト《ルビ》 または |ベーステキスト《ルビ》)
        # 縦線、ベーステキスト、ルビをキャプチャし、<ruby>タグ形式に置換
        # ベーステキストとルビは非貪欲マッチ(.+?)を使用
        (re.compile(r'[｜|](.+?)《(.+?)》'),
         lambda m: f'<ruby>{m.group(1)}<rp>(</rp><rt>{m.group(2)}</rt><rp>)</rp></ruby>'),

        # パターン3: 暗黙的なルビ（漢字 + 二重山括弧）(漢字《ひらがな/カタカナ》)
        # 漢字、ルビ(ひらがな/カタカナ)をキャプチャし、<ruby>タグ形式に置換
        (re.compile(r'([一-龠々・]+)《([ぁ-んァ-ヶー・]+)》'),
         lambda m: f'<ruby>{m.group(1)}<rp>(</rp><rt>{m.group(2)}</rt><rp>)</rp></ruby>'),

        # パターン4: 暗黙的なルビ（漢字 + 括弧）(漢字(ひらがな/カタカナ))
        # 漢字、ルビ(ひらがな/カタカナ)をキャプチャし、<ruby>タグ形式に置換
        (re.compile(r'([一-龠々・]+)\(([ぁ-んァ-ヶー・]+)\)'),
         lambda m: f'<ruby>{m.group(1)}<rp>(</rp><rt>{m.group(2)}</rt><rp>)</rp></ruby>'),
        (re.compile(r'([一-龠々・]+)（([ぁ-んァ-ヶー・]+)）'),
         lambda m: f'<ruby>{m.group(1)}<rp>(</rp><rt>{m.group(2)}</rt><rp>)</rp></ruby>'),
    ]

    processed_text = text
    # 定義した優先順位で各パターンをテキストに適用
    for pattern_compiled, replacement_func in patterns:
        processed_text = pattern_compiled.sub(replacement_func, processed_text)

    return processed_text


def create_epub(config):
    book = epub.EpubBook()
    set_metadata(book, config)
    add_cover_image(book, config)
    css = get_css_file(config)
    book.add_item(css)
    create_content(book, config)
    save_epub(book, config)


def add_cover_image(book, config):
    """
    EPUBにカバー画像を追加する
    :param book: EPUB Book object
    :param config: Configuration dictionary
    """
    cover_file = config.get('cover_image', COVER_IMAGE)
    mimetypes.init()
    media_type, _ = mimetypes.guess_type(cover_file)
    if os.path.exists(cover_file):
        with open(cover_file, 'rb') as f:
            cover_data = f.read()
        book.set_cover(cover_file, cover_data)
        print(f"カバー画像 {cover_file} を追加しました")
    else:
        print(f"カバー画像 {cover_file} が見つかりません。")


def save_epub(book, config):
    """
    EPUBファイルの保存
    :param book: EPUB Book object
    :param config: Configuration dictionary
    """
    try:
        output_file = config.get('output_file', OUTPUT_FILE)
        epub.write_epub(output_file, book, {
            "epub3_pages": True, "epub3_landmark": True})
        print(f"EPUBファイル {output_file} の保存しました")
    except Exception as e:
        print(f"EPUBファイル {output_file} の保存に失敗しました: {e}")


def get_css_file(config):
    """
    CSSファイルをEPUBに追加する
    :param book: EPUB Book object
    :param config: Configuration dictionary
    """
    css_file = config.get('css_file', CSS_FILE)
    with open(css_file, 'r', encoding='utf-8') as f:
        style = f.read()
    style_item = epub.EpubItem(
        uid="style_default", file_name=css_file, media_type="text/css", content=style)
    return style_item


if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_FILE

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        book_config = config.get('book_settings', {})
    except Exception as e:
        print(f"{config_file} を読み込み時にエラーが発生しました: {e}")

    create_epub(book_config)
