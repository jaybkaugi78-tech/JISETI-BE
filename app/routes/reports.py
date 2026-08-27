import io
import os
import re
import uuid

from urllib.parse import urlparse

import cloudinary.uploader

from flask import (
    Blueprint,
    jsonify,
    request,
    current_app,
    send_from_directory,
)

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from werkzeug.utils import secure_filename

from PIL import (
    Image,
    ImageOps,
    UnidentifiedImageError,
)

from app.extensions import db
from app.models import Report, StatusHistory


reports_bp = Blueprint(
    "reports",
    __name__,
)


VALID_TYPES = {
    "RED_FLAG",
    "INTERVENTION",
}


IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif",
}


VIDEO_EXTENSIONS = {
    "mp4",
    "mov",
    "webm",
}


ALLOWED_MEDIA_EXTENSIONS = (
    IMAGE_EXTENSIONS
    | VIDEO_EXTENSIONS
)


def allowed_media(filename):
    return (
        "." in filename
        and filename
        .rsplit(".", 1)[1]
        .lower()
        in ALLOWED_MEDIA_EXTENSIONS
    )


def compress_image(
    file,
    extension,
):
    file.stream.seek(0)

    image = Image.open(
        file.stream
    )

    image = ImageOps.exif_transpose(
        image
    )

    image.thumbnail(
        (1920, 1920),
        Image.Resampling.LANCZOS,
    )

    output = io.BytesIO()

    if extension in {
        "jpg",
        "jpeg",
    }:
        if image.mode not in {
            "RGB",
            "L",
        }:
            image = image.convert(
                "RGB"
            )

        image.save(
            output,
            format="JPEG",
            quality=82,
            optimize=True,
            progressive=True,
        )

    elif extension == "webp":
        if image.mode not in {
            "RGB",
            "RGBA",
        }:
            image = image.convert(
                "RGB"
            )

        image.save(
            output,
            format="WEBP",
            quality=82,
            method=6,
        )

    elif extension == "png":
        image.save(
            output,
            format="PNG",
            optimize=True,
            compress_level=9,
        )

    elif extension == "gif":
        image.save(
            output,
            format="GIF",
            optimize=True,
        )

    output.seek(0)

    return output


def save_media_files(files):
    saved_files = []

    for file in files:
        if (
            not file
            or not file.filename
        ):
            continue

        if not allowed_media(
            file.filename
        ):
            continue

        safe_name = secure_filename(
            file.filename
        )

        extension = (
            safe_name
            .rsplit(".", 1)[1]
            .lower()
        )

        public_id = (
            "jiseti/reports/"
            f"{uuid.uuid4().hex}"
        )

        try:
            if extension in IMAGE_EXTENSIONS:
                compressed_file = compress_image(
                    file,
                    extension,
                )

                result = cloudinary.uploader.upload(
                    compressed_file,
                    public_id=public_id,
                    resource_type="image",
                )

            else:
                file.stream.seek(0)

                result = cloudinary.uploader.upload(
                    file.stream,
                    public_id=public_id,
                    resource_type="video",
                )

            secure_url = result.get(
                "secure_url"
            )

            if secure_url:
                saved_files.append(
                    secure_url
                )

        except (
            UnidentifiedImageError,
            OSError,
        ) as error:
            print(
                "Media processing failed:",
                error,
            )

        except Exception as error:
            print(
                "Cloudinary upload failed:",
                error,
            )

    return saved_files


def is_cloudinary_url(value):
    return (
        isinstance(value, str)
        and value.startswith(
            "https://res.cloudinary.com/"
        )
    )


def cloudinary_resource_type(url):
    if "/video/upload/" in url:
        return "video"

    return "image"


def cloudinary_public_id_from_url(url):
    try:
        parsed_url = urlparse(url)

        if "/upload/" not in parsed_url.path:
            return None

        upload_path = parsed_url.path.split(
            "/upload/",
            1,
        )[1]

        path_parts = upload_path.split("/")

        if (
            path_parts
            and re.fullmatch(
                r"v\d+",
                path_parts[0],
            )
        ):
            path_parts = path_parts[1:]

        public_id = "/".join(
            path_parts
        )

        public_id = os.path.splitext(
            public_id
        )[0]

        return public_id

    except Exception:
        return None


def delete_cloudinary_media(url):
    public_id = (
        cloudinary_public_id_from_url(
            url
        )
    )

    if not public_id:
        return

    resource_type = (
        cloudinary_resource_type(
            url
        )
    )

    try:
        cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type,
            invalidate=True,
        )

    except Exception as error:
        print(
            "Cloudinary delete failed:",
            error,
        )


def delete_local_media(filename):
    upload_folder = os.path.join(
        current_app.root_path,
        "uploads",
        "reports",
    )

    file_path = os.path.join(
        upload_folder,
        filename,
    )

    if os.path.exists(
        file_path
    ):
        try:
            os.remove(
                file_path
            )

        except OSError as error:
            print(
                "Local media delete failed:",
                error,
            )


@reports_bp.get("")
@jwt_required()
def list_reports():
    user_id = int(
        get_jwt_identity()
    )

    reports = (
        Report.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            Report.created_at.desc()
        )
        .all()
    )

    return jsonify({
        "reports": [
            report.to_dict()
            for report in reports
        ]
    }), 200


@reports_bp.post("")
@jwt_required()
def create_report():
    if request.is_json:
        data = (
            request.get_json()
            or {}
        )

        media_files = []

    else:
        data = (
            request.form.to_dict()
        )

        media_files = (
            request.files.getlist(
                "media"
            )
        )

    report_type = (
        data.get("type")
        or ""
    ).upper().replace(
        "-",
        "_",
    )

    if report_type not in VALID_TYPES:
        return jsonify({
            "error":
                "type must be RED_FLAG or INTERVENTION"
        }), 400

    title = (
        data.get("title")
        or ""
    ).strip()

    description = (
        data.get("description")
        or ""
    ).strip()

    if (
        not title
        or not description
    ):
        return jsonify({
            "error":
                "title and description are required"
        }), 400

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    try:
        latitude = (
            float(latitude)
            if latitude not in (
                None,
                "",
            )
            else None
        )

        longitude = (
            float(longitude)
            if longitude not in (
                None,
                "",
            )
            else None
        )

    except (
        TypeError,
        ValueError,
    ):
        return jsonify({
            "error":
                "latitude and longitude must be valid numbers"
        }), 400

    saved_media = save_media_files(
        media_files
    )

    report = Report(
        user_id=int(
            get_jwt_identity()
        ),

        type=report_type,

        title=title,

        description=description,

        status="DRAFT",

        location_name=data.get(
            "location_name"
        ),

        latitude=latitude,

        longitude=longitude,

        media=saved_media,
    )

    db.session.add(
        report
    )

    db.session.commit()

    return jsonify({
        "message":
            "report created",

        "report":
            report.to_dict(),
    }), 201


@reports_bp.get(
    "/public"
)
def public_reports():
    reports = (
        Report.query
        .filter(
            Report.status.in_([
                "UNDER INVESTIGATION",
                "RESOLVED",
            ])
        )
        .order_by(
            Report.created_at.desc()
        )
        .all()
    )

    public_items = []

    for report in reports:
        data = report.to_dict()

        data.pop(
            "user_id",
            None,
        )

        data.pop(
            "created_by",
            None,
        )

        data.pop(
            "user",
            None,
        )

        public_items.append(
            data
        )

    return jsonify({
        "reports":
            public_items
    }), 200


@reports_bp.get(
    "/public/<int:report_id>"
)
def public_report_detail(
    report_id
):
    report = db.session.get(
        Report,
        report_id,
    )

    if not report:
        return jsonify({
            "error":
                "report not found"
        }), 404

    if report.status not in {
        "UNDER INVESTIGATION",
        "RESOLVED",
    }:
        return jsonify({
            "error":
                "report is not publicly available"
        }), 404

    data = report.to_dict()

    data.pop(
        "user_id",
        None,
    )

    data.pop(
        "created_by",
        None,
    )

    data.pop(
        "user",
        None,
    )

    return jsonify({
        "report":
            data
    }), 200


@reports_bp.get(
    "/notifications"
)
@jwt_required()
def notifications():
    user_id = int(
        get_jwt_identity()
    )

    history_items = (
        db.session.query(
            StatusHistory,
            Report,
        )
        .join(
            Report,
            StatusHistory.report_id
            == Report.id,
        )
        .filter(
            Report.user_id
            == user_id
        )
        .order_by(
            StatusHistory
            .changed_at
            .desc()
        )
        .all()
    )

    notification_items = []

    for (
        history,
        report,
    ) in history_items:
        notification_items.append({
            "id":
                history.id,

            "report_id":
                report.id,

            "report_title":
                report.title,

            "old_status":
                history.old_status,

            "new_status":
                history.new_status,

            "changed_at": (
                history.changed_at.isoformat()
                if history.changed_at
                else None
            ),

            "is_read":
                history.is_read,
        })

    return jsonify({
        "notifications":
            notification_items
    }), 200


@reports_bp.patch(
    "/notifications/read-all"
)
@jwt_required()
def mark_all_notifications_read():
    user_id = int(
        get_jwt_identity()
    )

    histories = (
        db.session.query(
            StatusHistory
        )
        .join(
            Report,
            StatusHistory.report_id
            == Report.id,
        )
        .filter(
            Report.user_id
            == user_id,

            StatusHistory
            .is_read
            .is_(False),
        )
        .all()
    )

    for history in histories:
        history.is_read = True

    db.session.commit()

    return jsonify({
        "message":
            "all notifications marked as read",

        "updated":
            len(histories),
    }), 200


@reports_bp.patch(
    "/notifications/<int:notification_id>/read"
)
@jwt_required()
def mark_notification_read(
    notification_id
):
    user_id = int(
        get_jwt_identity()
    )

    history = db.session.get(
        StatusHistory,
        notification_id,
    )

    if not history:
        return jsonify({
            "error":
                "notification not found"
        }), 404

    report = db.session.get(
        Report,
        history.report_id,
    )

    if (
        not report
        or report.user_id
        != user_id
    ):
        return jsonify({
            "error":
                "you cannot access this notification"
        }), 403

    history.is_read = True

    db.session.commit()

    return jsonify({
        "message":
            "notification marked as read",

        "notification": {
            "id":
                history.id,

            "report_id":
                report.id,

            "report_title":
                report.title,

            "old_status":
                history.old_status,

            "new_status":
                history.new_status,

            "changed_at": (
                history.changed_at.isoformat()
                if history.changed_at
                else None
            ),

            "is_read":
                history.is_read,
        },
    }), 200


@reports_bp.get(
    "/media/<path:filename>"
)
def get_report_media(
    filename
):
    upload_folder = os.path.join(
        current_app.root_path,
        "uploads",
        "reports",
    )

    return send_from_directory(
        upload_folder,
        filename,
    )


@reports_bp.get(
    "/<int:report_id>"
)
@jwt_required()
def get_report(
    report_id
):
    report = db.session.get(
        Report,
        report_id,
    )

    if not report:
        return jsonify({
            "error":
                "report not found"
        }), 404

    if report.user_id != int(
        get_jwt_identity()
    ):
        return jsonify({
            "error":
                "you cannot view this report"
        }), 403

    data = report.to_dict()

    data["status_history"] = [
        history.to_dict()
        for history
        in report.status_history
    ]

    return jsonify({
        "report":
            data
    }), 200


@reports_bp.put(
    "/<int:report_id>"
)
@jwt_required()
def update_report(
    report_id
):
    report = db.session.get(
        Report,
        report_id,
    )

    user_id = int(
        get_jwt_identity()
    )

    if not report:
        return jsonify({
            "error":
                "report not found"
        }), 404

    if report.user_id != user_id:
        return jsonify({
            "error":
                "you cannot edit this report"
        }), 403

    if report.status != "DRAFT":
        return jsonify({
            "error":
                "only DRAFT reports can be edited"
        }), 403

    data = (
        request.get_json()
        or {}
    )

    editable_fields = [
        "title",
        "description",
        "location_name",
        "latitude",
        "longitude",
    ]

    for field in editable_fields:
        if field in data:
            setattr(
                report,
                field,
                data[field],
            )

    db.session.commit()

    return jsonify({
        "message":
            "report updated",

        "report":
            report.to_dict(),
    }), 200


@reports_bp.delete(
    "/<int:report_id>"
)
@jwt_required()
def delete_report(
    report_id
):
    report = db.session.get(
        Report,
        report_id,
    )

    user_id = int(
        get_jwt_identity()
    )

    if not report:
        return jsonify({
            "error":
                "report not found"
        }), 404

    if report.user_id != user_id:
        return jsonify({
            "error":
                "only the creator can delete this report"
        }), 403

    if report.status != "DRAFT":
        return jsonify({
            "error":
                "only DRAFT reports can be deleted"
        }), 403

    for media_item in (
        report.media or []
    ):
        if is_cloudinary_url(
            media_item
        ):
            delete_cloudinary_media(
                media_item
            )

        else:
            delete_local_media(
                media_item
            )

    db.session.delete(
        report
    )

    db.session.commit()

    return jsonify({
        "message":
            "report deleted"
    }), 200