#!/usr/bin/env python3
"""Convert Markdown files to PDF with custom fonts.

This script is designed to be used by the Deep Research Agent's file_manager subagent.
It enforces security by only allowing conversions within the agent_workspace directory.

Usage:
    python convert_md_to_pdf.py <input.md>

The PDF will be saved in the same directory as the input markdown file.

Fonts:
    - Display (headings): Cormorant Garamond (serif)
    - Body (text): Inter (sans-serif)

Requirements:
    - markdown-pdf (installed in .venv)
"""

import argparse
import sys
from pathlib import Path


def validate_workspace_path(md_path: Path, workspace_dir: Path) -> tuple[bool, str]:
    """Validate that the markdown file is within the allowed workspace.

    Args:
        md_path: Path to the markdown file
        workspace_dir: Path to the allowed workspace directory

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Resolve absolute paths
        md_absolute = md_path.resolve()
        workspace_absolute = workspace_dir.resolve()

        # Check if md file is within workspace
        try:
            md_absolute.relative_to(workspace_absolute)
        except ValueError:
            return False, f"Security Error: File must be within {workspace_absolute}"

        # Check if file exists
        if not md_absolute.exists():
            return False, f"Error: File not found: {md_path}"

        # Check if it's a file (not directory)
        if not md_absolute.is_file():
            return False, f"Error: Not a file: {md_path}"

        # Check if it's a markdown file
        if md_absolute.suffix.lower() != '.md':
            return False, f"Error: File must have .md extension: {md_path}"

        return True, ""

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def convert_md_to_pdf(
    md_path: Path,
    font_display: str = "Cormorant Garamond",
    font_body: str = "Inter"
) -> tuple[bool, str, Path | None]:
    """Convert markdown file to PDF with custom fonts.

    Args:
        md_path: Path to the markdown file
        font_display: Font family for headings (default: Cormorant Garamond)
        font_body: Font family for body text (default: Inter)

    Returns:
        Tuple of (success, message, pdf_path)
    """
    try:
        from markdown_pdf import MarkdownPdf, Section

        # Generate PDF path (same directory, same name, .pdf extension)
        pdf_path = md_path.with_suffix('.pdf')

        # Read markdown content
        md_content = md_path.read_text(encoding='utf-8')

        # Create PDF with custom styling (no TOC to avoid library bugs)
        # Note: We pass CSS directly to MarkdownPdf constructor, not as part of the content
        pdf = MarkdownPdf(toc_level=0)

        # Set custom CSS via meta tags (markdown-pdf specific approach)
        pdf.meta["css"] = f"""
            @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400;1,500;1,600;1,700&family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap');

            body {{
                font-family: '{font_body}', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px;
            }}

            h1, h2, h3, h4, h5, h6 {{
                font-family: '{font_display}', serif;
                color: #1a1a1a;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
                font-weight: 600;
            }}

            h1 {{
                font-size: 2.5em;
                border-bottom: 3px solid #333;
                padding-bottom: 0.3em;
            }}

            h2 {{
                font-size: 2em;
                border-bottom: 2px solid #666;
                padding-bottom: 0.25em;
            }}

            h3 {{
                font-size: 1.5em;
            }}

            p {{
                margin-bottom: 1em;
                text-align: justify;
            }}

            code {{
                font-family: 'Courier New', monospace;
                background-color: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 0.9em;
            }}

            pre {{
                background-color: #f4f4f4;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                border-left: 4px solid #333;
            }}

            pre code {{
                background-color: transparent;
                padding: 0;
            }}

            blockquote {{
                border-left: 4px solid #ccc;
                margin-left: 0;
                padding-left: 20px;
                color: #666;
                font-style: italic;
            }}

            a {{
                color: #0066cc;
                text-decoration: none;
            }}

            a:hover {{
                text-decoration: underline;
            }}

            ul, ol {{
                margin-bottom: 1em;
                padding-left: 2em;
            }}

            li {{
                margin-bottom: 0.5em;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 1em;
            }}

            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }}

            th {{
                background-color: #f4f4f4;
                font-weight: 600;
                font-family: '{font_display}', serif;
            }}

            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 1em auto;
            }}
        """

        # Add section with ONLY markdown content (CSS is separate)
        pdf.add_section(Section(md_content))

        # Save PDF
        pdf.save(str(pdf_path))

        return True, f"Successfully converted {md_path.name} to {pdf_path.name}", pdf_path

    except ImportError:
        return False, "Error: markdown-pdf library not found. Install with: pip install markdown-pdf", None
    except Exception as e:
        return False, f"Conversion error: {str(e)}", None


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Convert Markdown to PDF with custom fonts (agent workspace only)"
    )
    parser.add_argument(
        "input_md",
        type=str,
        help="Path to the input markdown file (must be in agent_workspace)"
    )
    parser.add_argument(
        "--font-display",
        type=str,
        default="Cormorant Garamond",
        help="Font for headings (default: Cormorant Garamond)"
    )
    parser.add_argument(
        "--font-body",
        type=str,
        default="Inter",
        help="Font for body text (default: Inter)"
    )

    args = parser.parse_args()

    # Get paths
    md_path = Path(args.input_md)

    # Find workspace directory (assuming script is in src/scripts_for_agent)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    workspace_dir = project_root / "agent_workspace"

    # Validate workspace path
    is_valid, error_msg = validate_workspace_path(md_path, workspace_dir)
    if not is_valid:
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    print(f"Converting: {md_path}")
    print(f"Fonts: {args.font_display} (display), {args.font_body} (body)")
    print()

    # Convert to PDF
    success, message, pdf_path = convert_md_to_pdf(
        md_path,
        font_display=args.font_display,
        font_body=args.font_body
    )

    if success:
        print(f"✅ {message}")
        print(f"   Output: {pdf_path}")
        sys.exit(0)
    else:
        print(f"❌ {message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
