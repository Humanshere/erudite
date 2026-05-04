from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .permissions import IsAdmin
from .serializers import RegisterSerializer, UserSerializer
from .serializers import BenchmarkSelfieSerializer

from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.base import ContentFile


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class BenchmarkSelfieView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = BenchmarkSelfieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selfie = serializer.validated_data["selfie"]

        # compress/resize to speed up encoding
        from PIL import Image
        import io
        import face_recognition

        img = Image.open(selfie)
        # respect EXIF orientation
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        max_dim = 800
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)

        # compute face encoding
        image_np = face_recognition.load_image_file(buf)
        # try hog first (fast); if no faces, try cnn if available
        encodings = face_recognition.face_encodings(image_np)
        if not encodings:
            # diagnostic: try face_locations and cnn fallback
            locs_hog = face_recognition.face_locations(image_np, model="hog")
            print(f"Benchmark selfie: hog detected {len(locs_hog)} faces, image size={image_np.shape}")
            if not locs_hog:
                try:
                    locs_cnn = face_recognition.face_locations(image_np, model="cnn")
                    print(f"Benchmark selfie: cnn detected {len(locs_cnn)} faces")
                    if locs_cnn:
                        encodings = face_recognition.face_encodings(image_np, known_face_locations=locs_cnn)
                except Exception:
                    # cnn may not be available; ignore
                    pass
            if not encodings:
                return Response({"detail": "No face detected in the uploaded image."}, status=400)
        encoding = encodings[0].tolist()

        # save compressed selfie and encoding
        user = request.user
        filename = f"benchmark_{user.id}.jpg"
        user.benchmark_selfie.save(filename, ContentFile(buf.getvalue()), save=False)
        user.benchmark_face_encoding = encoding
        user.save()

        return Response({"detail": "Benchmark selfie saved."}, status=200)


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = User.objects.all().order_by("id")

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs


class AuthTokenView(TokenObtainPairView):
    pass


class AuthTokenRefreshView(TokenRefreshView):
    pass
