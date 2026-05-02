package com.example.erudite

import android.Manifest
import android.content.Context
import android.net.Uri
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.example.erudite.ui.theme.EruditeTheme
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.launch
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.Executors
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine

class CameraController(val captureSelfie: suspend () -> ByteArray?)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val repo = StudentAttendanceRepository(applicationContext)

        setContent {
            EruditeTheme {
                StudentAttendanceApp(repo = repo)
            }
        }
    }
}

@Composable
private fun StudentAttendanceApp(repo: StudentAttendanceRepository) {
    var loading by remember { mutableStateOf(true) }
    var user by remember { mutableStateOf<UserResponse?>(null) }
    var errorMessage by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        val me = repo.tryRestoreSession()
        user = me
        loading = false
    }

    if (loading) {
        Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                CircularProgressIndicator()
                Text("Checking saved login...", modifier = Modifier.padding(top = 12.dp))
            }
        }
        return
    }

    if (user == null) {
        LoginScreen(
            errorMessage = errorMessage,
            onLogin = { email, password ->
                errorMessage = ""
                val loginResult = repo.login(email, password)
                if (loginResult.isSuccess) {
                    val me = repo.fetchMe()
                    if (me?.role == "student") {
                        user = me
                    } else {
                        repo.logout()
                        errorMessage = "Only student accounts are allowed in this app."
                    }
                } else {
                    errorMessage = loginResult.exceptionOrNull()?.message ?: "Login failed"
                }
            },
        )
    } else {
        ScannerScreen(
            user = user!!,
            repo = repo,
            onLogout = {
                repo.logout()
                user = null
            },
        )
    }
}

@Composable
private fun LoginScreen(
    errorMessage: String,
    onLogin: suspend (email: String, password: String) -> Unit,
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(20.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Text("Student Login", style = MaterialTheme.typography.headlineSmall)
            Text(
                "Login once and scan classroom QR for attendance.",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 6.dp, bottom = 16.dp),
            )

            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Email") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text("Password") },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 10.dp),
                singleLine = true,
            )

            if (errorMessage.isNotBlank()) {
                Text(
                    text = errorMessage,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 10.dp),
                )
            }

            Button(
                onClick = {
                    if (busy) return@Button
                    busy = true
                    scope.launch {
                        onLogin(email.trim(), password)
                        busy = false
                    }
                },
                enabled = !busy && email.isNotBlank() && password.isNotBlank(),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp),
            ) {
                if (busy) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                } else {
                    Text("Login")
                }
            }
        }
    }
}

@Composable
private fun ScannerScreen(
    user: UserResponse,
    repo: StudentAttendanceRepository,
    onLogout: () -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var cameraController by remember { mutableStateOf<CameraController?>(null) }

    var cameraPermissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED,
        )
    }
    var locationPermissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED,
        )
    }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        cameraPermissionGranted = granted
    }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        locationPermissionGranted = granted
    }

    var statusText by remember { mutableStateOf("Point camera at class QR code") }
    var busy by remember { mutableStateOf(false) }
    var lastScanned by remember { mutableStateOf("") }
    var lastScanTs by remember { mutableLongStateOf(0L) }
    val scope = rememberCoroutineScope()

    val onDetected: (String) -> Unit = onDetected@{ rawValue ->
        val now = System.currentTimeMillis()
        if (busy) return@onDetected
        if (rawValue == lastScanned && now - lastScanTs < 2500) return@onDetected

        lastScanned = rawValue
        lastScanTs = now
        busy = true
        statusText = "Submitting attendance..."

        scope.launch {
            val token = extractToken(rawValue)
            if (token.isBlank()) {
                statusText = "Invalid QR payload."
                busy = false
                return@launch
            }

            // Attempt to get last known location (best-effort). Requires location permission.
            var lat: Double? = null
            var lon: Double? = null
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED
            ) {
                try {
                    val lm = context.getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
                    val l = lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER)
                        ?: lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER)
                    if (l != null) {
                        lat = l.latitude
                        lon = l.longitude
                    }
                } catch (ex: Exception) {
                    Log.w("EruditeScanner", "Could not fetch last known location", ex)
                }
            } else {
                statusText = "Location permission not granted; tap to allow."
            }

            // Capture selfie (front camera) if controller available; this will briefly switch cameras.
            var selfieBytes: ByteArray? = null
            try {
                selfieBytes = cameraController?.captureSelfie()
            } catch (ex: Exception) {
                Log.w("EruditeScanner", "Selfie capture failed", ex)
            }

            val result = repo.scanAttendance(token, lat, lon, selfieBytes)
            statusText = if (result.isSuccess) {
                result.getOrNull()?.detail ?: "Attendance marked."
            } else {
                result.exceptionOrNull()?.message ?: "Scan failed"
            }
            busy = false
        }
    }

    Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text("Hi, ${user.full_name}")
                    Text("Student QR Attendance", style = MaterialTheme.typography.titleMedium)
                }
                TextButton(onClick = onLogout) { Text("Logout") }
            }

            if (!cameraPermissionGranted) {
                Text(
                    "Camera permission is required to scan QR.",
                    modifier = Modifier.padding(top = 16.dp),
                )
                Button(
                    onClick = { cameraPermissionLauncher.launch(Manifest.permission.CAMERA) },
                    modifier = Modifier.padding(top = 8.dp),
                ) {
                    Text("Grant Camera Permission")
                }
            } else {
                if (!locationPermissionGranted) {
                    Text(
                        "Location permission is required to include your location with the scan.",
                        modifier = Modifier.padding(top = 12.dp),
                    )
                    Button(
                        onClick = { locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION) },
                        modifier = Modifier.padding(top = 8.dp),
                    ) {
                        Text("Grant Location Permission")
                    }
                }
                CameraQrScanner(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(380.dp)
                        .padding(top = 16.dp),
                    lifecycleOwner = lifecycleOwner,
                    onDetected = onDetected,
                    onControllerReady = { cameraController = it },
                )
            }

            Text(
                text = statusText,
                modifier = Modifier.padding(top = 14.dp),
                color = if (statusText.contains("failed", ignoreCase = true) || statusText.contains("invalid", ignoreCase = true)) {
                    MaterialTheme.colorScheme.error
                } else {
                    MaterialTheme.colorScheme.onSurface
                },
            )
        }
    }
}

@Composable
private fun CameraQrScanner(
    modifier: Modifier,
    lifecycleOwner: androidx.lifecycle.LifecycleOwner,
    onDetected: (String) -> Unit,
    onControllerReady: (CameraController) -> Unit = {},
) {
    val context = LocalContext.current
    val options = remember {
        BarcodeScannerOptions.Builder()
            .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
            .build()
    }
    val scanner = remember { BarcodeScanning.getClient(options) }

    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            val previewView = PreviewView(ctx)
            val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)

            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()
                var preview = androidx.camera.core.Preview.Builder().build().also {
                    it.surfaceProvider = previewView.surfaceProvider
                }

                var analysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()

                val analyzer = object : ImageAnalysis.Analyzer {
                    override fun analyze(imageProxy: ImageProxy) {
                        processImageProxy(scanner, imageProxy, onDetected)
                    }
                }

                analysis.setAnalyzer(ContextCompat.getMainExecutor(ctx), analyzer)

                try {
                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(
                        lifecycleOwner,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        preview,
                        analysis,
                    )
                } catch (ex: Exception) {
                    Log.e("EruditeScanner", "Camera bind failed", ex)
                }

                // Controller: capture selfie by briefly switching to front camera and using ImageCapture
                val controller = CameraController(captureSelfie = suspendCoroutine { cont ->
                    val mainExec = ContextCompat.getMainExecutor(ctx)
                    try {
                        val imageCapture = androidx.camera.core.ImageCapture.Builder().build()
                        // Bind front camera for capture
                        try {
                            cameraProvider.unbindAll()
                            cameraProvider.bindToLifecycle(lifecycleOwner, CameraSelector.DEFAULT_FRONT_CAMERA, imageCapture)
                        } catch (bindEx: Exception) {
                            cont.resumeWithException(bindEx)
                            return@suspendCoroutine
                        }

                        val tmpFile = java.io.File(ctx.cacheDir, "selfie_${System.currentTimeMillis()}.jpg")
                        val outputOptions = androidx.camera.core.ImageCapture.OutputFileOptions.Builder(tmpFile).build()
                        imageCapture.takePicture(outputOptions, mainExec, object : androidx.camera.core.ImageCapture.OnImageSavedCallback {
                            override fun onImageSaved(outputFileResults: androidx.camera.core.ImageCapture.OutputFileResults) {
                                try {
                                    val bytes = tmpFile.readBytes()
                                    // Rebind back camera preview and analysis
                                    try {
                                        preview = androidx.camera.core.Preview.Builder().build().also {
                                            it.surfaceProvider = previewView.surfaceProvider
                                        }
                                        analysis = ImageAnalysis.Builder()
                                            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                                            .build()
                                        analysis.setAnalyzer(ContextCompat.getMainExecutor(ctx), analyzer)
                                        cameraProvider.unbindAll()
                                        cameraProvider.bindToLifecycle(
                                            lifecycleOwner,
                                            CameraSelector.DEFAULT_BACK_CAMERA,
                                            preview,
                                            analysis,
                                        )
                                    } catch (rebindEx: Exception) {
                                        Log.e("EruditeScanner", "Failed to rebind back camera", rebindEx)
                                    }
                                    cont.resume(bytes)
                                } catch (e: Exception) {
                                    cont.resumeWithException(e)
                                }
                            }

                            override fun onError(exception: androidx.camera.core.ImageCaptureException) {
                                // Attempt to rebind back camera
                                try {
                                    preview = androidx.camera.core.Preview.Builder().build().also {
                                        it.surfaceProvider = previewView.surfaceProvider
                                    }
                                    analysis = ImageAnalysis.Builder()
                                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                                        .build()
                                    analysis.setAnalyzer(ContextCompat.getMainExecutor(ctx), analyzer)
                                    cameraProvider.unbindAll()
                                    cameraProvider.bindToLifecycle(
                                        lifecycleOwner,
                                        CameraSelector.DEFAULT_BACK_CAMERA,
                                        preview,
                                        analysis,
                                    )
                                } catch (rebindEx: Exception) {
                                    Log.e("EruditeScanner", "Failed to rebind after capture error", rebindEx)
                                }
                                cont.resumeWithException(exception)
                            }
                        })
                    } catch (e: Exception) {
                        cont.resumeWithException(e)
                    }
                })

                onControllerReady(controller)
            }, ContextCompat.getMainExecutor(ctx))

            previewView
        },
    )
}

private fun processImageProxy(
    scanner: com.google.mlkit.vision.barcode.BarcodeScanner,
    imageProxy: ImageProxy,
    onDetected: (String) -> Unit,
) {
    val mediaImage = imageProxy.image
    if (mediaImage == null) {
        imageProxy.close()
        return
    }

    val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
    scanner.process(image)
        .addOnSuccessListener { barcodes ->
            barcodes.firstOrNull()?.rawValue?.let(onDetected)
        }
        .addOnCompleteListener {
            imageProxy.close()
        }
}

private fun extractToken(rawValue: String): String {
    val trimmed = rawValue.trim()
    if (trimmed.contains("attendance_token=")) {
        return Uri.parse(trimmed).getQueryParameter("attendance_token") ?: ""
    }
    return trimmed
}

private data class LoginRequest(val email: String, val password: String)
private data class LoginResponse(val access: String, val refresh: String)
private data class ScanRequest(val token: String, val latitude: Double? = null, val longitude: Double? = null)
private data class ScanResponse(val detail: String)
private data class RefreshRequest(val refresh: String)
private data class RefreshResponse(val access: String)

private data class UserResponse(
    val id: Int,
    val email: String,
    val full_name: String,
    val role: String,
)

private interface EruditeApi {
    @POST("auth/login/")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @POST("auth/refresh/")
    suspend fun refresh(@Body body: RefreshRequest): RefreshResponse

    @GET("auth/me/")
    suspend fun me(): UserResponse

    @POST("attendance/qr-sessions/scan/")
    suspend fun scan(@Body body: ScanRequest): ScanResponse
}

private class StudentAttendanceRepository(context: Context) {
    private val prefs = context.getSharedPreferences("erudite_student_prefs", Context.MODE_PRIVATE)
    private val accessKey = "access_token"
    private val refreshKey = "refresh_token"

    private var accessToken: String? = prefs.getString(accessKey, null)
    private var refreshToken: String? = prefs.getString(refreshKey, null)

    private val api: EruditeApi

    init {
        val authInterceptor = Interceptor { chain ->
            val token = accessToken
            val reqBuilder = chain.request().newBuilder()
            if (!token.isNullOrBlank()) {
                reqBuilder.addHeader("Authorization", "Bearer $token")
            }
            chain.proceed(reqBuilder.build())
        }

        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val rawClient = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(rawClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        api = retrofit.create(EruditeApi::class.java)
    }

    suspend fun login(email: String, password: String): Result<Unit> {
        return runCatching {
            val tokens = api.login(LoginRequest(email = email, password = password))
            saveTokens(tokens.access, tokens.refresh)
        }
    }

    suspend fun fetchMe(): UserResponse? {
        return runCatching { api.me() }.getOrNull()
    }

    suspend fun tryRestoreSession(): UserResponse? {
        if (accessToken.isNullOrBlank()) return null

        val me = fetchMe()
        if (me != null) return me

        val refreshed = refreshAccessToken()
        return if (refreshed) fetchMe() else null
    }

    suspend fun scanAttendance(token: String, latitude: Double? = null, longitude: Double? = null): Result<ScanResponse> {
        return runCatching {
            api.scan(ScanRequest(token = token, latitude = latitude, longitude = longitude))
        }.recoverCatching {
            if (refreshAccessToken()) {
                api.scan(ScanRequest(token = token, latitude = latitude, longitude = longitude))
            } else {
                throw it
            }
        }
    }

    suspend fun scanAttendance(token: String, latitude: Double? = null, longitude: Double? = null, selfie: ByteArray? = null): Result<ScanResponse> {
        return runCatching {
            val url = BASE_URL + "attendance/qr-sessions/scan/"
            val builder = MultipartBody.Builder().setType(MultipartBody.FORM)
            builder.addFormDataPart("token", token)
            if (latitude != null) builder.addFormDataPart("latitude", latitude.toString())
            if (longitude != null) builder.addFormDataPart("longitude", longitude.toString())
            var tmpFile: java.io.File? = null
            if (selfie != null) {
                tmpFile = java.io.File.createTempFile("selfie", ".jpg", context.cacheDir)
                tmpFile.outputStream().use { it.write(selfie) }
                val mediaType = "image/jpeg".toMediaTypeOrNull()
                builder.addFormDataPart("selfie", "selfie.jpg", tmpFile.asRequestBody(mediaType))
            }

            val requestBody = builder.build()
            val requestBuilder = Request.Builder().url(url).post(requestBody)
            val tokenHeader = accessToken
            if (!tokenHeader.isNullOrBlank()) {
                requestBuilder.addHeader("Authorization", "Bearer $tokenHeader")
            }

            val req = requestBuilder.build()
            val resp = rawClient.newCall(req).execute()
            val body = resp.body?.string() ?: throw Exception("Empty response")
            if (!resp.isSuccessful) throw Exception("Scan failed: $body")
            val gson = com.google.gson.Gson()
            gson.fromJson(body, ScanResponse::class.java)
        }.recoverCatching {
            if (refreshAccessToken()) {
                scanAttendance(token, latitude, longitude, selfie)
            } else {
                throw it
            }
        }
    }

    fun logout() {
        accessToken = null
        refreshToken = null
        prefs.edit().remove(accessKey).remove(refreshKey).apply()
    }

    private suspend fun refreshAccessToken(): Boolean {
        val refresh = refreshToken ?: return false
        val refreshed = runCatching { api.refresh(RefreshRequest(refresh)) }.getOrNull() ?: return false
        saveTokens(refreshed.access, refresh)
        return true
    }

    private fun saveTokens(access: String, refresh: String) {
        accessToken = access
        refreshToken = refresh
        prefs.edit().putString(accessKey, access).putString(refreshKey, refresh).apply()
    }

    companion object {
        // Android emulator localhost mapping. Use your machine IP for physical devices.
        private const val BASE_URL = "http://172.20.10.9:8000/api/"
    }
}