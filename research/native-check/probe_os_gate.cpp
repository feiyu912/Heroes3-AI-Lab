// Mirrors the platform gate in the pinned training fork's MLClient.cpp.
#if defined(VCMI_MAC)
#define LIBEXT "dylib"
#elif defined(VCMI_UNIX)
#define LIBEXT "so"
#else
#error "Unsupported OS"
#endif
int main() { return 0; }
