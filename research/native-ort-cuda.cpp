// Optional experiment: append CUDA to native ONNX session options, without
// rebuilding or changing the VCMI game engine. Enabled only by LAB_ONNX_CUDA=1.
#include <onnxruntime_c_api.h>
#include <dlfcn.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <set>
#include <string>

namespace {
const OrtApiBase *original_base() {
    using Entry=const OrtApiBase*(ORT_API_CALL*)() noexcept;
    // Python loads its connector with RTLD_LOCAL, so RTLD_NEXT cannot see
    // that dependency group. Resolve the pinned runtime by its own handle.
    static void *handle=[] {
        const auto *directory=std::getenv("LAB_NATIVE_ONNX_LIBRARY");
        if(!directory)return static_cast<void*>(nullptr);
        return dlopen((std::string(directory)+"/libonnxruntime.so.1").c_str(),RTLD_NOW|RTLD_LOCAL);
    }();
    static auto entry=reinterpret_cast<Entry>(handle?dlsym(handle,"OrtGetApiBase"):nullptr);
    if(!entry) { std::fprintf(stderr,"Missing original OrtGetApiBase\n");std::abort(); }
    return entry();
}
const OrtApi *original_api() { return original_base()->GetApi(ORT_API_VERSION); }

OrtStatus *ORT_API_CALL create_options(OrtSessionOptions **options) noexcept {
    const auto *api=original_api();
    if(auto *status=api->CreateSessionOptions(options))return status;
    OrtCUDAProviderOptionsV2 *cuda=nullptr;
    if(auto *status=api->CreateCUDAProviderOptions(&cuda))return status;
    const char *keys[]={"device_id","gpu_mem_limit","arena_extend_strategy","use_tf32","do_copy_in_default_stream"};
    const char *values[]={"0","536870912","kSameAsRequested","0","1"};
    auto *status=api->UpdateCUDAProviderOptions(cuda,keys,values,5);
    if(!status)status=api->SessionOptionsAppendExecutionProvider_CUDA_V2(*options,cuda);
    api->ReleaseCUDAProviderOptions(cuda);
    if(status)return status;
    if(const auto *prefix=std::getenv("LAB_ONNX_PROFILE")) {
        const auto filename=std::string(prefix)+"-"+std::to_string(getpid());
        if(auto *failure=api->EnableProfiling(*options,filename.c_str()))return failure;
    }
    std::fprintf(stderr,"LAB_ONNX_CUDA enabled pid=%d, arena=512MiB, TF32=off\n",getpid());
    return nullptr;
}

OrtStatus *ORT_API_CALL run(OrtSession *session,const OrtRunOptions *options,
    const char *const *names,const OrtValue *const *inputs,size_t input_count,
    const char *const *output_names,size_t output_count,OrtValue **outputs) noexcept {
    const auto *api=original_api();
    auto *status=api->Run(session,options,names,inputs,input_count,output_names,output_count,outputs);
    if(status || !std::getenv("LAB_ONNX_PROFILE"))return status;
    static std::mutex mutex;static std::set<OrtSession*> profiled;
    std::lock_guard<std::mutex> guard(mutex);
    if(profiled.insert(session).second) {
        OrtAllocator *allocator=nullptr;
        if(auto *failure=api->GetAllocatorWithDefaultOptions(&allocator))return failure;
        char *filename=nullptr;
        if(auto *failure=api->SessionEndProfiling(session,allocator,&filename))return failure;
        std::fprintf(stderr,"LAB_ONNX_CUDA profile=%s\n",filename);
        allocator->Free(allocator,filename);
    }
    return nullptr;
}

const OrtApi *ORT_API_CALL get_api(uint32_t version) noexcept {
    if(version!=ORT_API_VERSION || !std::getenv("LAB_ONNX_CUDA"))return original_base()->GetApi(version);
    static const OrtApi wrapped=[] {
        OrtApi table=*original_api();
        table.CreateSessionOptions=create_options;
        table.Run=run;
        return table;
    }();
    return &wrapped;
}
const char *ORT_API_CALL get_version() noexcept { return original_base()->GetVersionString(); }
}

extern "C" const OrtApiBase *ORT_API_CALL OrtGetApiBase() noexcept {
    static const OrtApiBase wrapped{get_api,get_version};
    return &wrapped;
}
