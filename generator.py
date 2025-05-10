#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
from ebooklib import epub
import re
import yaml


def convert_line_text_to_html(line_text):
    """
    1行のテキストを処理し、ルビ変換（行頭以外）、縦中横変換を行います。
    """
    processed_line = line_text

    # 1. ルビ変換 (行頭以外)
    # パターン: 漢字(親文字) + （ルビ文字）
    # 親文字: [一-龠々]+ (漢字および繰り返し記号「々」の1文字以上)
    # ルビ文字: [^（）]+? (始め括弧と終わり括弧以外の1文字以上、非貪欲マッチ)
    # 正規表現のコールバック関数を使って、行頭かどうかを判定
    def ruby_replace_callback(match):
        # マッチオブジェクトのstart()で行頭かどうかを判定
        # この関数は1行単位で呼び出されるため、match.start(0) == 0 が行頭を意味する
        # if match.start(0) == 0:
        #     return match.group(0) # 行頭なら変換せず元の文字列を返す
        # else:
        parent_text = match.group(1)
        ruby_text = match.group(2)
        return f'<ruby>{parent_text}<rt>{ruby_text}</rt></ruby>'

    # 注意: 漢字の範囲 [一-龠] は一般的なもの。より広範な文字を親文字に含めたい場合は調整が必要。
    processed_line = re.sub(r'([一-龠々]+)（([^（）]+?)）', ruby_replace_callback, processed_line)

    # 2. 縦中横変換 ( [[...]] で囲まれた半角英数字記号2～4文字程度)
    def tcy_replace_callback(match):
        content = match.group(1)
        # 縦中横の対象とする文字種と長さをチェック
        if re.fullmatch(r'[a-zA-Z0-9.,\-:/+]{2,4}', content):
            return f'<span class="tcy">{content}</span>'
        return match.group(0)   # 条件に合わなければ元の文字列を返す (例: [[長すぎる文字列]])

    processed_line = re.sub(r'\[\[([a-zA-Z0-9.,\-:/+]{2,4}?)\]\]', tcy_replace_callback, processed_line)

    return processed_line


def convert_full_text_to_html(text_content):
    """
    複数行のテキストコンテンツ全体をHTMLに変換します。
    段落処理、各行のルビ・縦中横処理を行います。
    """
    # Windowsの改行コード(CRLF)をLFに統一し、3つ以上の連続改行を2つにまとめる
    processed_text = text_content.replace('\r\n', '\n')
    processed_text = re.sub(r'\n{3,}', '\n\n', processed_text)

    html_paragraphs = []
    # 2つの改行で段落に分割
    for para_text in processed_text.strip().split('\n\n'):
        if para_text.strip():   # 空の段落は無視
            html_lines_in_paragraph = []
            # 段落内の各行に分割
            for single_line in para_text.split('\n'):
                if single_line.strip():     # 行が空でなければ処理
                    # 各行に対してルビと縦中横の変換を適用
                    processed_html_line = convert_line_text_to_html(single_line.strip())
                    html_lines_in_paragraph.append(processed_html_line)

            if html_lines_in_paragraph:
                # 処理された行を<br />で結合し、<p>タグで囲む
                html_paragraphs.append('<p>' + '<br />'.join(html_lines_in_paragraph) + '</p>')

    return '\n'.join(html_paragraphs)


def create_vertical_epub(config):
    """
    YAML設定に基づいて、ディレクトリ内のテキストファイルを読み込み、
    縦書きのEPUBファイルを生成します。ルビ、縦中横、ページ区切りに対応。

    Args:
        config (dict): YAMLファイルから読み込まれた設定情報。
    """

    book_config = config.get('book_settings', {})
    css_config = config.get('css_settings', {})

    book_title = book_config.get('title', "無題")
    book_author = book_config.get('author', "不明な著者")
    book_language = book_config.get('language', 'ja')
    input_dir = book_config.get('input_directory')
    output_epub_file = book_config.get('output_file')
    cover_image_path = book_config.get('cover_image')

    if not input_dir or not output_epub_file:
        print("エラー: 設定ファイルに 'input_directory' または 'output_file' が指定されていません。")
        return

    config_dir = os.path.dirname(os.path.abspath(config.get('_config_file_path', '.')))
    input_dir = os.path.join(config_dir, input_dir)
    output_epub_file = os.path.join(config_dir, output_epub_file)
    if cover_image_path:
        cover_image_path = os.path.join(config_dir, cover_image_path)
        if not os.path.exists(cover_image_path):
            print(f"警告: 指定されたカバー画像 '{cover_image_path}' が見つかりません。カバーなしで処理を続行します。")
            cover_image_path = None
    else:
        cover_image_path = None

    book = epub.EpubBook()
    book.set_identifier(f'urn:uuid:{os.urandom(16).hex()}')     # ランダムなUUIDを生成
    book.set_title(book_title)
    book.set_language(book_language)
    book.add_author(book_author)
    book.direction = 'rtl'

    # --- 縦書き用CSS ---
    font_family = css_config.get('font_family', '"游明朝", "Yu Mincho", "Hiragino Mincho ProN", "ヒラギノ明朝 ProN W3", "MS Mincho", "ＭＳ 明朝", serif')
    line_height = css_config.get('line_height', 1.8)
    margin_vertical = css_config.get('margin_vertical', '20px')
    margin_horizontal = css_config.get('margin_horizontal', '30px')

    style_content = f"""
@namespace epub "http://www.idpf.org/2007/ops";
body {{
    font-family: {font_family};
    writing-mode: vertical-rl;
    -webkit-writing-mode: vertical-rl;
    -epub-writing-mode: vertical-rl;
    -epub-line-break: normal;
    line-break: auto;
    text-orientation: mixed;
    orphans: 1;
    widows: 1;
    overflow-x: hidden;
    margin: {margin_vertical} {margin_horizontal};
    padding: 0;
}}
p {{
    margin: 0 0 1em 0; /* 縦書きでは段落の右側のマージン */
    line-height: {line_height};
    text-align: justify;
}}
h1, h2, h3, h4, h5, h6 {{
    font-weight: bold;
    margin-top: 1.5em; /* 縦書きでは見出しの右側のマージン */
    margin-bottom: 0.8em; /* 縦書きでは見出しの左側のマージン */
    line-height: 1.5;
    break-before: page; /* 各章(h1)の前に改ページを強制 (ファイル区切り) */
}}
/* 縦中横用スタイル */
.tcy {{
    text-combine-upright: all;
    /* -webkit-text-combine: horizontal; */ /* 古いWebKit用、現在はほぼ不要 */
}}
/* ルビの基本的なスタイル (多くのリーダーはデフォルトで対応) */
ruby rt {{
    font-size: 0.6em; /* ルビ文字のサイズを親文字より小さくする */
    /* 必要に応じてルビの位置調整用のスタイルを追加できますが、リーダー依存性が高まります */
    /* ruby-position: over; (CSS3 Ruby, EPUB3では writing-mode との組み合わせで自動調整されることが多い) */
}}
ruby rtc {{ /* ルビコンテナのスタイル (通常不要) */
}}
img {{
    max-width: 100%;
    max-height: 90vh;
    object-fit: contain;
    display: block;
    margin: 1em auto;
}}
"""
    default_css = epub.EpubItem(uid="style_default",
                                file_name="style/default.css",
                                media_type="text/css",
                                content=style_content.encode('utf-8'))
    book.add_item(default_css)

    # --- カバー画像設定 ---
    actual_cover_item = None
    if cover_image_path and os.path.exists(cover_image_path):
        try:
            with open(cover_image_path, 'rb') as f:
                cover_data = f.read()
            cover_filename = os.path.basename(cover_image_path)
            cover_ext = os.path.splitext(cover_filename)[1].lower()
            media_type = 'image/jpeg'
            if cover_ext == '.png': media_type = 'image/png'
            elif cover_ext == '.gif': media_type = 'image/gif'
            elif cover_ext == '.svg': media_type = 'image/svg+xml'

            epub_image_filename = f'cover_image{cover_ext}'
            epub_image_path_in_epub = f'images/{epub_image_filename}'

            cover_html_content = f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{book_language}" lang="{book_language}" style="margin:0; padding:0;"><head><title>カバー</title><meta charset="utf-8"/><style>
body {{ writing-mode: horizontal-tb !important; text-align: center; margin: 0; padding: 0; height: 100vh; display: flex; justify-content: center; align-items: center; background-color: #f0f0f0; }}
img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}</style></head><body epub:type="cover">
<img src="{epub_image_path_in_epub}" alt="カバー画像" /></body></html>"""
            actual_cover_item = epub.EpubHtml(uid='coverpage', title='カバー', file_name='cover.xhtml',
                                              content=cover_html_content.encode('utf-8'), lang=book_language)
            book.add_item(actual_cover_item)
            cover_image_epub_item = epub.EpubItem(uid='cover_image_data', file_name=epub_image_path_in_epub,
                                                  media_type=media_type, content=cover_data)
            book.add_item(cover_image_epub_item)
            book.add_metadata('OPF', 'meta', '', {'name': 'cover', 'content': 'cover_image_data'})
        except Exception as e:
            print(f"カバー画像の処理中にエラーが発生しました: {e}")
            actual_cover_item = None
    else:
        if book_config.get('cover_image'):
            print(f"情報: カバー画像パス '{book_config.get('cover_image')}' は指定されましたが見つかりませんでした。")
        else:
            print("情報: カバー画像は設定されていません。")

    # --- テキストファイル読み込みとチャプター作成 ---
    if not os.path.isdir(input_dir):
        print(f"エラー: 指定された入力ディレクトリ '{input_dir}' が存在しません。")
        return

    txt_files_unsorted = glob.glob(os.path.join(input_dir, '*.txt'))

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
    txt_files = sorted(txt_files_unsorted, key=natural_sort_key)

    if not txt_files:
        print(f"情報: 入力ディレクトリ '{input_dir}' に .txt ファイルが見つかりませんでした。")

    chapters = []
    toc_links = []

    for i, txt_file_path in enumerate(txt_files):
        file_name_only = os.path.basename(txt_file_path)
        chapter_title = re.sub(r'^エピソード[0-9]+：', '', os.path.splitext(file_name_only)[0])

        try:
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                content_text = f.read()
        except Exception as e:
            print(f"ファイル '{txt_file_path}' の読み込み中にエラー: {e}")
            continue

        # ルビ・縦中横処理を含むHTML変換
        html_content = convert_full_text_to_html(content_text)

        safe_chapter_title_for_filename = re.sub(r'[^\x00-\x7F]+', '', chapter_title)
        if not safe_chapter_title_for_filename:
            safe_chapter_title_for_filename = f"chapter_{i+1}"
        else:
            safe_chapter_title_for_filename = re.sub(r'\s+', '_', safe_chapter_title_for_filename)
        xhtml_file_name = f"c_{i+1}_{safe_chapter_title_for_filename[:20]}.xhtml"

        chapter_obj = epub.EpubHtml(title=chapter_title,
                                    file_name=xhtml_file_name,
                                    lang=book_language)
        chapter_obj.content = f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{book_language}" lang="{book_language}">
<head>
    <meta charset="utf-8" />
    <title>{chapter_title}</title>
    <link rel="stylesheet" type="text/css" href="style/default.css" />
</head>
<body>
    <h1>{chapter_title}</h1>
    {html_content}
</body>
</html>
""".encode('utf-8')
        chapter_obj.add_item(default_css)   # CSSを各チャプターにリンク
        book.add_item(chapter_obj)
        chapters.append(chapter_obj)
        toc_links.append(epub.Link(xhtml_file_name, chapter_title, f"toc_chap_{i+1}"))

    # --- 目次 (TOC), NCX, Nav の設定 ---
    book.toc = tuple(toc_links)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # --- Spine (本文の表示順序) の設定 ---
    spine_items = ['nav']
    if actual_cover_item:
        spine_items.append(actual_cover_item)
    spine_items.extend(chapters)
    book.spine = spine_items

    # --- EPUBファイル書き出し ---
    try:
        os.makedirs(os.path.dirname(output_epub_file), exist_ok=True)
        epub.write_epub(output_epub_file, book, {"epub3_pages": True, "epub3_landmark": True})
        print(f"EPUBファイル '{output_epub_file}' を正常に生成しました。")
    except Exception as e:
        print(f"EPUBファイルの書き出し中にエラーが発生しました: {e}")


# --- メイン処理 ---
if __name__ == '__main__':
    config_file_name = 'config.yaml'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(script_dir, config_file_name)

    if not os.path.exists(config_file_path):
        print(f"エラー: 設定ファイル '{config_file_path}' が見つかりません。")
        print("スクリプトと同じディレクトリに config.yaml を作成してください。内容は以下の例を参考にしてください：")
        sample_config_content = """
# EPUB書籍の設定 (config.yaml)
book_settings:
  title: "私の縦書き小説（ルビ対応版）"
  author: "AI 次郎"
  language: "ja"
  input_directory: "docs"  # このディレクトリを作成し、txtファイルを入れてください
  output_file: "MyVerticalNovel_Ruby.epub"
  cover_image: "my_cover.jpg"       # (任意) カバー画像ファイル名

# CSS設定 (任意、なければスクリプト内のデフォルト値を使用)
# css_settings:
#   font_family: '"Noto Serif CJK JP", serif'
#   line_height: 1.9
"""
        print("\n--- config.yaml の例 ---")
        print(sample_config_content)
        print("-----------------------\n")
        print("テキストファイル内でルビを振りたい箇所は「漢字（かんじ）」のように、")
        print("縦中横にしたい箇所は [[ABC]] のように囲んでください。")
    else:
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            if config_data is None:
                print(f"エラー: 設定ファイル '{config_file_path}' が空か、または無効なYAML形式です。")
            else:
                config_data['_config_file_path'] = config_file_path
                create_vertical_epub(config_data)
        except yaml.YAMLError as e:
            print(f"設定ファイル '{config_file_path}' の解析中にエラーが発生しました: {e}")
        except Exception as e:
            print(f"処理中に予期せぬエラーが発生しました: {e}")
