# app.py

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles  # Imported StaticFiles
from pydantic import BaseModel
import os
import logging
import matplotlib
import matplotlib.pyplot as plt
from fpdf import FPDF
import re
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import uuid
from tempfile import NamedTemporaryFile

# Use Agg backend for matplotlib in headless environments
matplotlib.use('Agg')

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the API key header
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Retrieve the API key from environment variables for security
API_KEY = os.getenv("API_KEY", "default_key")

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        logger.warning(f"Unauthorized access attempt with API Key: {api_key}")
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key

# Ensure 'files' and 'fonts' directories exist
os.makedirs("files", exist_ok=True)
os.makedirs("fonts", exist_ok=True)

# Mount the files directory to serve static files
app.mount("/files", StaticFiles(directory="files"), name="files")

# Input model for PDF generation
class GeneratePDFRequest(BaseModel):
    executive_summary: str
    portfolio_summary: str
    tax_loss_harvesting_analysis: str
    reinvestment_strategy: str
    portfolio_outlook: str
    actionable_next_steps: str
    irs_compliance_warning: str

# Improved Markdown table parser
def parse_markdown_table(markdown):
    try:
        rows = [row.strip() for row in markdown.strip().split("\n") if row.strip()]

        if len(rows) < 3:
            raise ValueError(f"Invalid table markdown: Insufficient rows. Markdown: {markdown}")

        header = rows[0].split("|")
        separator = rows[1].split("|")

        # Normalize and validate separator row
        separator = [cell.strip() for cell in separator]
        if not all(cell == "" or re.match(r"^-+$", cell) for cell in separator):
            raise ValueError(f"Invalid table markdown: Separator row must contain only '---'. Markdown: {markdown}")

        data = [row.split("|") for row in rows[2:]]
        max_cols = max(len(header), *(len(row) for row in data))
        header = [cell.strip() for cell in header] + [""] * (max_cols - len(header))
        data = [[cell.strip() for cell in row] + [""] * (max_cols - len(row)) for row in data]

        logger.info("Markdown table parsed successfully.")
        return [header] + data
    except Exception as e:
        logger.error(f"Error parsing markdown table: {e}", exc_info=True)
        raise

# Table image generator
def create_dynamic_table_image(data, filename="table.png"):
    try:
        if not data:
            logger.warning("Empty data for table image")
            return

        col_widths = [max(len(str(cell)) for cell in col) for col in zip(*data)]
        total_width = sum(col_widths)
        fig_width = min(15, total_width * 0.5)
        fig_height = len(data) * 0.5

        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ax.axis("off")
        table = ax.table(cellText=data[1:], colLabels=data[0], loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("lightgrey")
            if len(str(cell.get_text().get_text())) > 30:
                cell.get_text().set_wrap(True)

        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Table image '{filename}' created successfully.")
    except Exception as e:
        logger.error(f"Error creating table image '{filename}': {e}", exc_info=True)
        raise

# Custom PDF class
class StyledPDF(FPDF):
    def __init__(self):
        super().__init__()
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            FONT_DIR = os.path.join(BASE_DIR, "fonts")
            FONT_PATH_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
            FONT_PATH_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
            FONT_PATH_ITALIC = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")
            FONT_PATH_BOLD_ITALIC = os.path.join(FONT_DIR, "DejaVuSans-BoldOblique.ttf")

            # Add regular and bold fonts
            self.add_font("DejaVu", "", FONT_PATH_REGULAR, uni=True)
            self.add_font("DejaVu", "B", FONT_PATH_BOLD, uni=True)

            # Add italic and bold italic fonts
            self.add_font("DejaVu", "I", FONT_PATH_ITALIC, uni=True)
            self.add_font("DejaVu", "BI", FONT_PATH_BOLD_ITALIC, uni=True)

            logger.info("All DejaVu fonts added successfully.")
        except Exception as e:
            logger.error(f"Error adding fonts: {e}", exc_info=True)
            raise

    def header(self):
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            LOGO_PATH = os.path.join(BASE_DIR, "logo.png")
            if os.path.exists(LOGO_PATH):
                self.image(LOGO_PATH, x=10, y=8, w=30)
                logger.info("Logo added to PDF header.")
            else:
                logger.warning(f"Logo file not found at '{LOGO_PATH}'.")
            self.set_y(25)  # Move title below the logo
            self.set_font("DejaVu", "B", 16)
            self.set_text_color(102, 0, 204)  # Dark purple
            self.cell(0, 10, "Harvest & Invest: Portfolio Optimization Report", ln=1, align="C")
            self.ln(10)  # Extra spacing below the header
            logger.info("PDF header created successfully.")
        except Exception as e:
            logger.error(f"Error creating PDF header: {e}", exc_info=True)
            raise

    def add_section(self, title, content, is_disclaimer=False):
        try:
            if is_disclaimer:
                self.set_text_color(0, 0, 0)  # Black text
                self.set_font("DejaVu", "I", 8)  # Italic and smaller font
            else:
                self.set_text_color(153, 102, 255)  # Light purple
                self.set_font("DejaVu", "B", 12)

            self.cell(0, 10, txt=title, ln=True)
            self.ln(3)

            if not is_disclaimer:
                self.set_font("DejaVu", size=10)
                self.set_text_color(0, 0, 0)  # Reset to black for normal text

            self.render_content(content)
            self.ln(5)
            logger.info(f"Section '{title}' added successfully.")
        except Exception as e:
            logger.error(f"Error adding section '{title}': {e}", exc_info=True)
            raise

    def render_content(self, content):
        """
        Dynamically render text and tables from content.
        """
        try:
            lines = content.strip().split("\n")
            buffer = []
            in_table = False

            for line in lines:
                if "|" in line:
                    if not in_table:
                        if buffer:
                            self.multi_cell(0, 8, "\n".join(buffer).strip())
                            self.ln(5)
                            buffer = []
                        in_table = True
                    buffer.append(line.strip())
                else:
                    if in_table:
                        self.render_table("\n".join(buffer))
                        self.ln(10)
                        buffer = []
                        in_table = False
                    buffer.append(line)

            if in_table:
                self.render_table("\n".join(buffer))
                self.ln(10)
            elif buffer:
                self.multi_cell(0, 8, "\n".join(buffer).strip())
                self.ln(5)
            logger.info("Content rendered successfully.")
        except Exception as e:
            logger.error(f"Error rendering content: {e}", exc_info=True)
            raise

    def render_table(self, markdown_table):
        """
        Parse and render a table from markdown.
        """
        try:
            data = parse_markdown_table(markdown_table)
            data = self.clean_table_data(data)  # Remove blank columns
            with NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                filename = tmp_file.name
            create_dynamic_table_image(data, filename)  # Improved table rendering
            logger.info(f"Table image '{filename}' created successfully.")

            if os.path.exists(filename):
                img_width = self.w - 20  # Adjust for margins
                img_height = self.get_image_height(filename, img_width)
                if self.get_y() + img_height > self.h - 20:  # Check space for table
                    self.add_page()
                    logger.info("Added new page for table.")
                self.image(filename, x=10, y=self.get_y(), w=img_width)
                self.ln(img_height + 5)  # Add space after table
                logger.info(f"Table image '{filename}' added to PDF.")
                os.remove(filename)  # Clean up temporary file
                logger.info(f"Temporary table image '{filename}' removed.")
            else:
                logger.error(f"Table image '{filename}' does not exist.")
        except Exception as e:
            logger.error(f"Error rendering table: {e}", exc_info=True)
            raise

    def clean_table_data(self, data):
        """
        Remove blank columns from table data.
        """
        if not data:
            return data

        transposed = list(zip(*data))
        cleaned = [col for col in transposed if any(cell.strip() for cell in col)]
        return list(map(list, zip(*cleaned))) if cleaned else data

    def get_image_height(self, filename, width):
        """
        Calculate the height of the table image for given width.
        """
        img_width, img_height = self.get_image_dimensions(filename)
        aspect_ratio = img_height / img_width
        return width * aspect_ratio

    def get_image_dimensions(self, filename):
        """
        Get image dimensions using PIL.
        """
        from PIL import Image
        with Image.open(filename) as img:
            return img.size

# Static content
fixed_content = {
    "About This Report": (
        "This report outlines a strategy for optimizing your portfolio through tax-loss harvesting (TLH) "
        "and reinvestment. It is designed to align with your aggressive risk tolerance, sector preferences, "
        "and growth-oriented investment goals."
    )
}

disclaimer_text = (
    "This report is provided for informational purposes only and is based on the data and preferences you have shared. "
    "The recommendations contained herein are intended to assist in optimizing your portfolio in alignment with your "
    "stated investment goals, risk tolerance, and financial objectives.\n\n"
    "Market Risks: All investments involve risk, including the potential loss of principal. Past performance is not indicative "
    "of future results.\n"
    "Tax Considerations: Tax-loss harvesting recommendations are based on current IRS guidelines, which are subject to change. "
    "Consult a qualified tax advisor.\n"
    "No Guarantees: There is no guarantee that recommendations will achieve the desired outcomes.\n"
    "Dynamic Market Conditions: This report does not account for unforeseen market fluctuations or macroeconomic factors.\n\n"
    "Consult with legal, tax, and financial advisors before acting on any recommendations provided in this report."
)

# IBM COS Configuration using HMAC credentials
COS_HMAC_ACCESS_KEY = os.getenv("COS_HMAC_ACCESS_KEY_ID")
COS_HMAC_SECRET_KEY = os.getenv("COS_HMAC_SECRET_ACCESS_KEY")
COS_ENDPOINT = os.getenv("COS_ENDPOINT", "https://s3.us-south.cloud-object-storage.appdomain.cloud")
COS_BUCKET_NAME = os.getenv("COS_BUCKET_NAME")

if not all([COS_HMAC_ACCESS_KEY, COS_HMAC_SECRET_KEY, COS_ENDPOINT, COS_BUCKET_NAME]):
    logger.error("IBM COS HMAC credentials or bucket configuration not set in environment variables.")
    raise Exception("IBM COS HMAC credentials or bucket configuration not set in environment variables.")

# Create an IBM COS client with 's3v4' signature
try:
    cos = ibm_boto3.client(
        "s3",
        aws_access_key_id=COS_HMAC_ACCESS_KEY,
        aws_secret_access_key=COS_HMAC_SECRET_KEY,
        endpoint_url=COS_ENDPOINT,
        config=Config(signature_version='s3v4'),
        region_name='us-south'  # Specify your region
    )
    logger.info("IBM COS client initialized successfully with 's3v4' signature.")
except Exception as e:
    logger.error("Failed to initialize IBM COS client:", exc_info=True)
    raise

@app.post("/generate-pdf")
async def generate_pdf(request: Request, body: GeneratePDFRequest, api_key: str = Depends(get_api_key)):
    try:
        logger.info("Received request to generate PDF.")
        pdf = StyledPDF()
        pdf.add_page()
        logger.info("Initialized StyledPDF and added a new page.")

        # Add fixed content
        for title, content in fixed_content.items():
            logger.info(f"Adding fixed content section: {title}")
            pdf.add_section(title, content)

        # Add user-provided content
        for title, content in body.dict().items():
            formatted_title = title.replace("_", " ").title()
            logger.info(f"Adding user content section: {formatted_title}")
            pdf.add_section(formatted_title, content)

        # Add disclaimer
        logger.info("Adding disclaimer section.")
        pdf.add_section("Disclaimer", disclaimer_text, is_disclaimer=True)

        # Generate PDF as bytes
        pdf_output = pdf.output(dest='S').encode('latin1')  # Encode using 'latin1' as FPDF uses ISO-8859-1
        logger.info("Generated PDF output as bytes.")

        # Generate a unique object name
        unique_suffix = uuid.uuid4()
        object_name = f"Portfolio_Optimization_Report_{unique_suffix}.pdf"
        logger.info(f"Generated unique object name: {object_name}")

        # Upload the PDF to IBM COS with the unique object name
        try:
            cos.put_object(
                Bucket=COS_BUCKET_NAME,
                Key=object_name,
                Body=pdf_output,
                ContentType='application/pdf'
            )
            logger.info(f"PDF uploaded successfully as '{object_name}'.")
        except ClientError as e:
            logger.error(f"Error uploading PDF: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error uploading PDF to COS.")

        # Generate a pre-signed URL valid for 1 hour (3600 seconds)
        try:
            presigned_url = cos.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': COS_BUCKET_NAME,
                    'Key': object_name
                },
                ExpiresIn=432000  # URL validity in seconds
            )
            logger.info(f"Generated pre-signed URL: {presigned_url}")
        except ClientError as e:
            logger.error(f"Error generating pre-signed URL: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error generating pre-signed URL.")

        return {"message": "PDF generated successfully", "file_url": presigned_url}

    except Exception as e:
        logger.error(f"Error generating PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
