<component :is="'script'">
    const socket = io();
    console.log(socket)
</component>

<template class="block"> 
    <div class="mx-auto container">
        <div class="shadow-md mt-6 flex flex-wrap justify-between align-start bg-white overflow-hidden rounded-lg max-w-[10rem]">
            <div class="px-5 pt-5 pb-2 md:px-6 md:pt-6 lg:basis-2/5 flex flex-col items-start justify-between order-2 lg:order-1 max-w-[10rem]" style="">
                <div>
                    <h2 class="text-3xl font-semibold leading-10"></h2>
                    <p class="text-base font-light my-4 line-clamp-5 lg:line-clamp-4 xl:line-clamp-5">AA</p>
                </div>
            </div>
        </div>
    </div>
</template>