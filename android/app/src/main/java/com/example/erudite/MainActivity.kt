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

    var cameraPermissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED,
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        cameraPermissionGranted = granted
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

            val result = repo.scanAttendance(token)
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
                    onClick = { permissionLauncher.launch(Manifest.permission.CAMERA) },
                    modifier = Modifier.padding(top = 8.dp),
                ) {
                    Text("Grant Camera Permission")
                }
            } else {
                CameraQrScanner(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(380.dp)
                        .padding(top = 16.dp),
                    lifecycleOwner = lifecycleOwner,
                    onDetected = onDetected,
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
                val preview = androidx.camera.core.Preview.Builder().build().also {
                    it.surfaceProvider = previewView.surfaceProvider
                }

                val analysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()

                analysis.setAnalyzer(
                    ContextCompat.getMainExecutor(ctx),
                    object : ImageAnalysis.Analyzer {
                        override fun analyze(imageProxy: ImageProxy) {
                            processImageProxy(scanner, imageProxy, onDetected)
                        }
                    },
                )

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
private data class ScanRequest(val token: String)
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

        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
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

    suspend fun scanAttendance(token: String): Result<ScanResponse> {
        return runCatching {
            api.scan(ScanRequest(token = token))
        }.recoverCatching {
            if (refreshAccessToken()) {
                api.scan(ScanRequest(token = token))
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
        private const val BASE_URL = "http://10.0.2.2:8000/api/"
    }
}